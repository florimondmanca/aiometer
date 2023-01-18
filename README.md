# aiometer

[![Build Status](https://dev.azure.com/florimondmanca/public/_apis/build/status/florimondmanca.aiometer?branchName=master)](https://dev.azure.com/florimondmanca/public/_build/latest?definitionId=4&branchName=master)
[![Coverage](https://codecov.io/gh/florimondmanca/aiometer/branch/master/graph/badge.svg)](https://codecov.io/gh/florimondmanca/aiometer)
![Python versions](https://img.shields.io/pypi/pyversions/aiometer.svg)
[![Package version](https://badge.fury.io/py/aiometer.svg)](https://pypi.org/project/aiometer)

`aiometer` is a Python 3.7+ concurrency scheduling library compatible with `asyncio` and `trio` and inspired by [Trimeter](https://github.com/python-trio/trimeter). It makes it easier to execute lots of tasks concurrently while controlling concurrency limits (i.e. applying _[backpressure](https://lucumr.pocoo.org/2020/1/1/async-pressure/)_) and collecting results in a predictable manner.

**Content**

- [Example](#example)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
  - [Flow control](#flow-control)
  - [Running tasks](#running-tasks)
- [How To](#how-to)
- [API Reference](#api-reference)
- [Contributing](#contributing)
- [License](#license)

## Example

Let's use [HTTPX](https://github.com/encode/httpx) to make web requests concurrently...

_Try this code interactively using [IPython](https://ipython.org/install.html)._

```python
>>> import asyncio
>>> import functools
>>> import random
>>> import aiometer
>>> import httpx
>>>
>>> client = httpx.AsyncClient()
>>>
>>> async def fetch(client, request):
...     response = await client.send(request)
...     # Simulate extra processing...
...     await asyncio.sleep(2 * random.random())
...     return response.json()["json"]
...
>>> requests = [
...     httpx.Request("POST", "https://httpbin.org/anything", json={"index": index})
...     for index in range(100)
... ]
...
>>> # Send requests, and process responses as they're made available:
>>> async with aiometer.amap(
...     functools.partial(fetch, client),
...     requests,
...     max_at_once=10, # Limit maximum number of concurrently running tasks.
...     max_per_second=5,  # Limit request rate to not overload the server.
... ) as results:
...     async for data in results:
...         print(data)
...
{'index': 3}
{'index': 4}
{'index': 1}
{'index': 2}
{'index': 0}
...
>>> # Alternatively, fetch and aggregate responses into an (ordered) list...
>>> jobs = [functools.partial(fetch, client, request) for request in requests]
>>> results = await aiometer.run_all(jobs, max_at_once=10, max_per_second=5)
>>> results
[{'index': 0}, {'index': 1}, {'index': 2}, {'index': 3}, {'index': 4}, ...]
```

## Installation

_This project is in beta and maturing. Be sure to pin any dependencies to the latest minor._

```bash
pip install "aiometer==0.3.*"
```

## Features

- Concurrency management and throttling helpers.
- `asyncio` and `trio` support.
- Fully type annotated.
- 100% test coverage.

## Usage

### Flow control

The key highlight of `aiometer` is allowing you to apply flow control strategies in order to limit the degree of concurrency of your programs.

There are two knobs you can play with to fine-tune concurrency:

- `max_at_once`: this is used to limit the maximum number of concurrently running tasks at any given time. (If you have 100 tasks and set `max_at_once=10`, then `aiometer` will ensure that no more than 10 run at the same time.)
- `max_per_second`: this option limits the number of tasks spawned per second. This is useful to not overload I/O resources, such as servers that may have a rate limiting policy in place.

Example usage:

```python
>>> import asyncio
>>> import aiometer
>>> async def make_query(query):
...     await asyncio.sleep(0.05)  # Simulate a database request.
...
>>> queries = ['SELECT * from authors'] * 1000
>>> # Allow at most 5 queries to run concurrently at any given time:
>>> await aiometer.run_on_each(make_query, queries, max_at_once=5)
...
>>> # Make at most 10 queries per second:
>>> await aiometer.run_on_each(make_query, queries, max_per_second=10)
...
>>> # Run at most 10 concurrent jobs, spawning new ones at least every 5 seconds:
>>> async def job(id):
...     await asyncio.sleep(10)  # A very long task.
...
>>> await aiometer.run_on_each(job, range(100),  max_at_once=10, max_per_second=0.2)
```

### Running tasks

`aiometer` provides 4 different ways to run tasks concurrently in the form of 4 different run functions. Each function accepts all the options documented in [Flow control](#flow-control), and runs tasks in a slightly different way, allowing to address a variety of use cases. Here's a handy table for reference (see also the [API Reference](#api-reference)):

| Entrypoint      | Use case                                       |
| --------------- | ---------------------------------------------- |
| `run_on_each()` | Execute async callbacks in any order.          |
| `run_all()`     | Return results as an ordered list.             |
| `amap()`        | Iterate over results as they become available. |
| `run_any()`     | Return result of first completed function.     |

To illustrate the behavior of each run function, let's first setup a hello world async program:

```python
>>> import asyncio
>>> import random
>>> from functools import partial
>>> import aiometer
>>>
>>> async def get_greeting(name):
...     await asyncio.sleep(random.random())  # Simulate I/O
...     return f"Hello, {name}"
...
>>> async def greet(name):
...     greeting = await get_greeting(name)
...     print(greeting)
...
>>> names = ["Robert", "Carmen", "Lucas"]
```

Let's start with `run_on_each()`. It executes an async function once for each item in a list passed as argument:

```python
>>> await aiometer.run_on_each(greet, names)
'Hello, Robert!'
'Hello, Lucas!'
'Hello, Carmen!'
```

If we'd like to get the list of greetings in the same order as `names`, in a fashion similar to [`Promise.all()`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/all), we can use `run_all()`:

```python
>>> await aiometer.run_all([partial(get_greeting, name) for name in names])
['Hello, Robert', 'Hello, Carmen!', 'Hello, Lucas!']
```

`amap()` allows us to process each greeting as it becomes available (which means maintaining order is not guaranteed):

```python
>>> async with aiometer.amap(get_greeting, names) as greetings:
...     async for greeting in greetings:
...         print(greeting)
'Hello, Lucas!'
'Hello, Robert!'
'Hello, Carmen!'
```

Lastly, `run_any()` can be used to run async functions until the first one completes, similarly to [`Promise.any()`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/any):

```python
>>> await aiometer.run_any([partial(get_greeting, name) for name in names])
'Hello, Carmen!'
```

As a last fun example, let's use `amap()` to implement a no-threads async version of [sleep sort](https://rosettacode.org/wiki/Sorting_algorithms/Sleep_sort):

```python
>>> import asyncio
>>> from functools import partial
>>> import aiometer
>>> numbers = [0.3, 0.1, 0.6, 0.2, 0.7, 0.5, 0.5, 0.2]
>>> async def process(n):
...     await asyncio.sleep(n)
...     return n
...
>>> async with aiometer.amap(process, numbers) as results:
...     sorted_numbers = [n async for n in results]
...
>>> sorted_numbers
[0.1, 0.2, 0.2, 0.3, 0.5, 0.5, 0.6, 0.7]
```

## How To

### Multiple parametrized values in `run_on_each` and `amap`

`run_on_each` and `amap` only accept functions that accept a single positional argument (i.e. `(Any) -> Awaitable`).

So if you have a function that is parametrized by multiple values, you should refactor it to match this form.

This can generally be achieved like this:

1. Build a proxy container type (eg. a `namedtuple`), eg `T`.
2. Refactor your function so that its signature is now `(T) -> Awaitable`.
3. Build a list of these proxy containers, and pass it to `aiometer`.

For example, assuming you have a function that processes X/Y coordinates...

```python
async def process(x: float, y: float) -> None:
    pass

xs = list(range(100))
ys = list(range(100))

for x, y in zip(xs, ys):
    await process(x, y)
```

You could use it with `amap` by refactoring it like this:

```python
from typing import NamedTuple

# Proxy container type:
class Point(NamedTuple):
    x: float
    y: float

# Rewrite to accept a proxy as a single positional argument:
async def process(point: Point) -> None:
    x = point.x
    y = point.y
    ...

xs = list(range(100))
ys = list(range(100))

# Build a list of proxy containers:
points = [Point(x, y) for x, y in zip(x, y)]

# Use it:
async with aiometer.amap(process, points) as results:
    ...
```

## API Reference

### Common options

* `max_at_once` (_Optional_, `int`): the maximum number of concurrently running tasks at any given time.
* `max_per_second` (_Optional_, `int`): the maximum number of tasks spawned per second.

### `aiometer.run_on_each()`

**Signature**: _async_ aiometer.run_on_each(*async_fn*, *args*, *, *max_at_once=None*, *max_per_second=None*) -> *None*

Concurrently run the equivalent of `async_fn(arg) for arg in args`. Does not return any value. To get return values back, use [`aiometer.run_all()`](#aiometerrun_all).

### `aiometer.run_all()`

**Signature**: _async_ aiometer.run_all(*async_fns*, *max_at_once=None*, *max_per_second=None*) -> *list*

Concurrently run the `async_fns` functions, and return the list of results in the same order.

### `aiometer.amap()`

**Signature**: _async_ aiometer.amap(*async_fn*, *args*, *max_at_once=None*, *max_per_second=None*) -> *async iterator*

Concurrently run the equivalent of `async_fn(arg) for arg in args`, and return an async iterator that yields results as they become available.

### `aiometer.run_any()`

**Signature**: _async_ aiometer.run_any(*async_fns*, *max_at_once=None*, *max_per_second=None*) -> *Any*

Concurrently run the `async_fns` functions, and return the first available result.

## Contributing

See [CONTRIBUTING.md](./CONTRIBUTING.md).

## License

MIT
