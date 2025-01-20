# Chorus

Chorus is a tool for calling an OpenAI-compatible text generation API, in bulk, from the command line, ergonomically.

To do so "ergonomically" on the command line is an "interesting problem" from a UI perspective, which I've decided to approach by allowing the user to structure how they communicate settings to the system.

## Installation

Chorus depends on Python 3.9 or later, alone, without dependencies, and will run "out of the box" on recent versions of macOS and Ubuntu.

The script can be saved directly to any `/bin` directory, and set executable with `chmod +x`.

On Linux or macOS, you can do this with `curl` like so:

```bash
curl -o /usr/local/bin/chorus https://raw.githubusercontent.com/JoeCooper/chorus/refs/heads/master/chorus.py && chmod +x /usr/local/bin/chorus
```

## How It Works

In short, we need to build a plan featuring messages, content, requirements, settings, and an API key or base URL. Some of these have reasonable defaults. Some settings you will want to share between activities. Some settings you will want to override for a single activity. And some, you will want to override just once.

Chorus will read, in order:

1. The environment variable `OPENAI_API_KEY` (if set)
2. All files found under `~/.chorus/`
3. All files specified as command line arguments.
4. Arguments with `--` can override specific settings on the command line.

Chorus pays no mind to the file extension. It reads all files, whether specified or found in `~/.chorus/`, according to the same rules.

First, if the file begins with `{`, it is assumed to contain a JSON dictionary which can specify any of these plan properties:

| Property | Type | Default | Description |
| --- | --- | --- | --- |
| `apiKey` | string | Required | The API key to use for requests. |
| `baseUrl` | string | `https://api.openai.com/v1` | The base URL to use for requests. |
| `workers` | int | `16` | The number of workers to use for requests. |
| `requestsPerSecond` | int | `128` | The maximum number of requests per second to make. |
| `maxRetries` | int | `3` | The maximum number of retries to make for a request. |
| `output` | string | `csv` | The output format to use. |
| `model` | string | `gpt-4o-mini` | The model to use for requests. |
| `skip` | int | `0` | The number of samples to skip. |
| `messages` | array | Required | The messages to use for requests. |
| `jsonValidate` | bool | `false` | Whether to require the LLM's output is valid JSON. |
| `temperature` | float | `1.0` | The temperature to use for requests. |
| `samples` | array | `[]` | The samples to use for requests. |

If any property is specified twice, the latter claim will _override_ the former.

Any property can be overridden via command line arguments:

```bash
chorus planfile samplefile --model gpt-4o-mini --temperature 0.5
```

### Messages

A plan file is a JSON file that, minimally, features `messages`, an array of messages for a typical chat completion model.

```json
{
  "messages": [
    {"role": "system", "content": "You write a single sentence featuring the given word."},
    {"role": "user", "content": "phantom"},
    {"role": "assistant", "content": "The phantom of the opera is a ghost."}
  ]
}
```

Notice I do not include a final `user` message.

For each sample, Chorus will call the model, adding that sample to the `messages` array as a `user` message.

### Simple Samples File

Any file which does _not_ begin with `{` is assumed to contain a list of samples, one per line.

```
phantom
opera
Christine
```

When reading any such file, Chorus will add each sample to the plan.

### Samples on the command line

You can also specify samples on the command line, using the `--sample` argument. Note this is singular, and deviates from other properties.

```bash
chorus planfile --sample phantom --sample opera --sample Christine
```

### Multiple Sample Files

Unlike other properties, samples are _combined,_ and not overridden.

```bash
chorus planfile samplefile1 samplefile2
```

## Output

Chorus writes results to `stdout`, and faults to `stderr`.

Whereas order is not gauranteed, results are written together with the instigating sample.

### CSV

By default, Chorus writes CSV with two columns: `sample` and `content`.

```
sample,content
elytrum,The elytrum of the beetle shone brilliantly under the sunlight.
turnscrew,He expertly used a turnscrew to tighten the delicate machinery.
```

### JSONL

Chorus can write JSONL, in which each line is a JSON dictionary with `sample` and `content` properties.

```bash
chorus planfile samplefile --output jsonl
```

```jsonl
{"sample": "elytrum", "content": "The elytrum of the beetle shone brilliantly under the sunlight."}
{"sample": "turnscrew", "content": "He expertly used a turnscrew to tighten the delicate machinery."}
```

## Retries

For JSON validation failures, Chorus will retry immediately, with a non-zero `temperature`.

If `temperature` is set explicitly because `0.5`, it will be set to `0.5` for the retry.

This is done on the principle that the LLM, behaving (ideally) deterministically, will produce the same (unacceptable) output unless run with a non-zero `temperature`.

On HTTP `429`, Chorus will retry using randomized backoff.

## Example

In the `example` directory, you will find a plan file, a sample file, and a config file.

```bash
cd example
chorus config plan shortwords --apiKey sk-...
```

We could also run the same plan with a different sample file:

```bash
chorus config plan shortwords morewords --apiKey sk-...
```

Notice files are specified in order of precedence, ascending. Any claim found in `plan` can override any claim found in `config`, which in turn can override any claim found in `~/.chorus/config`.
