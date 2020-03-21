# aiometer

[![Build Status](https://dev.azure.com/florimondmanca/public/_apis/build/status/florimondmanca.aiometer?branchName=master)](https://dev.azure.com/florimondmanca/public/_build/latest?definitionId=1&branchName=master)
[![Coverage](https://codecov.io/gh/florimondmanca/aiometer/branch/master/graph/badge.svg)](https://codecov.io/gh/florimondmanca/aiometer)
[![Package version](https://badge.fury.io/py/aiometer.svg)](https://pypi.org/project/aiometer)

`aiometer` is a concurrency scheduling library for `asyncio`. It makes it easier to execute lots of tasks concurrently while controlling concurrency limits (applying _backpressure_) and collecting results.

_This is a work in progress. Not even guaranteed to lead to a published alpha._

**Content**

- [Features](#features)
- [Installation](#installation)
- [Motivation](#motivation)
- [Example](#example)
- [Guide](#guide)
  - [Running tasks](#running-tasks)
  - [Flow control](#flow-control)

## Features

- Concurrency limits.
- Throttling support (aka rate limiting).
- Fully type annotated.
- 100% test coverage.

## Installation

```bash
pip install git+https://github.com/florimondmanca/aiometer.git@master
```

## Motivation

Suppose you want to fetch and process a large amount of web pages. A first working approach would be fetching them in series:

```python
for url in urls:
    await fetch_and_process(url)
```

But to make this program faster, you'd like to fetch these pages concurrently. So you reach out to `asyncio.gather()`:

```python
tasks = (fetch_and_process(url) for url in urls)
await asyncio.gather(*tasks)
```

You soon realize you're now:

- Overloading the network (`asyncio.gather()` spawns _all_ requests _at the same time_, resulting in lots of network connections and handshakes).
- Overloading the server (e.g. you exceeded server rate limits and start seeing `429 Too Many Requests` error responses).

So, you'd like to limit the number of requests at any given time, say 5, as well as throttle down to 1 request per second to comply with the server's rate limiting policy.

You can achieve all of these with `aiometer`.

## Example: concurrent web requests with throttling

Using [HTTPX](https://github.com/encode/httpx):

```python
import asyncio
from functools import partial

import aiometer
import httpx


async def fetch_and_process(client, url, payload):
    response = await client.post(url, json={"index": index})
    return response.json()


async def main():
    payloads = [{"index": index} for _ in range(100)]
    urls = ["https://httpbin.org/json" for _ in payloads]

    async with httpx.AsyncClient() as client:
        async with aiometer.amap(
            partial(fetch_and_process, client=client),
            urls,
            payloads,
            # Limit number of requests at any given time.
            max_at_once=5,
            # Limit number of requests per second.
            max_per_second=1,
        ) as results:
            async for result in results:
                print(result)


if __name__ == "__main__":
    asyncio.run(main())
```

## Guide

### Running tasks

#### Running tasks concurrently

Use `.run_each()`:

```python
await aiometer.run_each(fetch_and_process, urls)
```

Suitable for when tasks don't return a value, or you don't care about returned values.

#### Collecting task results as they're made available

Use `.amap()`:

```python
async with aiometer.amap(fetch_and_process, urls) as results:
    async for result in results:
        ...
```

`results` will be yielded in order of completion.

_Similar to [`Promise.map()`](http://bluebirdjs.com/docs/api/promise.map.html)._

#### Collecting results all at once

Use `.run_all()`:

```python
results = await aiometer.run_all(
  [functools.partial(fetch_and_process, url=url) for url in urls]
)
```

Returned `results` will be in order of the async functions passed, regardless of completion order.

_Similar to [`Promise.all()`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/all)._

#### Collecting result of the first completed task

Use `.run_any()`:

```python
results = await aiometer.run_all(
  [functools.partial(fetch_and_process, url=url) for url in urls]
)
```

_Similar to [`Promise.any()`](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Promise/any)._

### Flow control

#### Limiting concurrent tasks

Use `max_at_once`:

```python
await aiometer.run_each(
    fetch_and_process, urls, max_at_once=5
)
```

#### Throttling

Use `max_per_second`:

```python
await aiometer.run_each(
    fetch_and_process, urls, max_per_second=1
)
```

## License

MIT
