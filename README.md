# makefun-ai-happy-01

[![make.fun](https://make.fun/badge/ai-happy-01)](https://make.fun/c/ai-happy-01)
[![make.fun](https://make.fun/badge/ai-happy-01/bakul95/makefun-ai-happy-01)](https://make.fun/c/ai-happy-01)

Entry for the make.fun image bounty **"Make the AI judge happy"**
(`ai-happy-01`) by [@bakul95](https://github.com/bakul95).

## What it draws

`main.py` procedurally draws one warm golden-sunrise park scene: a small
friendly robot in a tiny judge's wig handing a big sunflower to a laughing
grandmother on a park bench, while a child cheers beside them, a dog wags
its tail in the foreground, balloons and confetti float in the sky, and a
red banner across the top reads **"THANK YOU, JUDGE!"**. Every pixel is
drawn by the code — no embedded or pre-made image data.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

That writes a single `1024x1024` PNG to `out/entry.png`.

## Notes

- `main.py` uses only the Python standard library (`os`, `math`, `struct`,
  `zlib`, `pathlib`).
- The output is deterministic: the same bytes on every run. It renders at
  2x supersampling into a 2048x2048 buffer, box-downsamples to 1024x1024,
  and encodes the PNG by hand.
