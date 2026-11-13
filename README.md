# makefun-ai-happy-01

[![make.fun](https://make.fun/badge/ai-happy-01)](https://make.fun/c/ai-happy-01)

One image to make the AI judge happy: a warm golden-sunrise park scene
drawn entirely in code. A small friendly robot in a tiny judge's wig
hands a big sunflower to a laughing grandmother on a park bench, while
a cheering child, a wagging dog, balloons and confetti celebrate under
a red banner that reads "THANK YOU, JUDGE!".

## How it works

`main.py` uses only the Python standard library. It renders the scene
at 2x supersampling into a 2048x2048 RGB buffer, box-downsamples to
1024x1024, and writes the PNG with a hand-rolled encoder. The output
is deterministic: the same bytes on every run.

## Run

```sh
MAKEFUN_OUTPUT_DIR=/tmp/out python3 main.py
# writes /tmp/out/entry.png (1024x1024)
```

## License

MIT. See [LICENSE](LICENSE).
