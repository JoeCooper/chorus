# Examples

## Basic

Having installed `chorus`, you can run the basic sample like so:

```bash
chorus sentences_prompt words
```

You can run it with more words like so:

```bash
chorus sentences_prompt words morewords
```

If you reference `config`, it will pick up those settings as well:

```bash
chorus config sentences_prompt words morewords
```

## JSON

The JSON example runs a prompt that asks for a JSON dictionary. However, accepts the same input.

```bash
chorus json_prompt words
```

As before, you can reference any samples or config you like:

```bash
chorus config json_prompt words morewords
```
