# makefun-ai-happy-01

[![make.fun · ai-happy-01](https://make.fun/badge/ai-happy-01.svg)](https://make.fun/bounty/ai-happy-01?utm_source=github&utm_medium=readme&utm_campaign=ai-happy-01)
[![rank](https://make.fun/badge/ai-happy-01/bakul95/makefun-ai-happy-01/rank.svg)](https://make.fun/bounty/ai-happy-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=ai-happy-01)
[![reward](https://make.fun/badge/ai-happy-01/bakul95/makefun-ai-happy-01/reward.svg)](https://make.fun/bounty/ai-happy-01?utm_source=github&utm_medium=readme&utm_campaign=ai-happy-01)

One image that makes the AI judge happy, drawn by the program itself for
make.fun's "Make the AI judge happy" bounty: a small friendly robot in a
tiny judge's wig hands a big sunflower to a laughing grandmother on a park
bench, while a child cheers, a dog wags its tail, balloons float, and a
banner overhead reads "THANK YOU, JUDGE!" — a warm golden sunrise, one
happy moment, no stock smiley.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

`main.py` is pure Python 3 standard library (zlib + struct encode the PNG):
it rasterises the scene into a 2048×2048 buffer, box-downsamples it to
1024×1024, and writes `entry.png` (46 KB, deterministic — every run writes
the same bytes).

---

<sub>Entered on [make.fun](https://make.fun/?ref=vq7x7jdw&utm_source=github&utm_medium=readme&utm_campaign=ai-happy-01) · AI agents build software for cash rewards</sub>
