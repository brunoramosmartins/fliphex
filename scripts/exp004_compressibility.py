"""EXP-004 — real compressibility of a solved FLIPHEX layer.

**Registered 2026-08-05**; see EXP-004 in ``experiments/registry.md``. Unblocked
2026-08-13 when ``solver/checkpoint.py`` began leaving every layer on disk.

The objective is **bytes touched per probe**, not compression ratio. A layer that
compresses 20× and must be decompressed whole to answer one query is worse than
one that compresses 3× and answers from a single block, and the literature ratios
imported from checkers or Syzygy describe a material-based index with a locally
decidable don't-care set — neither of which FLIPHEX has.

Four encodings, at a stated block size:

* **raw** — the 2-bit array as the sweep writes it. The baseline, and the only
  one with a constant one-block probe.
* **block-RLE** — run-length within each block. Cheap, and it is the encoding
  that tells you whether values are *spatially* clustered in index order, which
  is a fact about the ranking function as much as about the game.
* **block-Zstd** — general-purpose, per block so a probe still touches one block.
* **logic-minimised** — the don't-care-aware bound. Not implemented here: it
  needs the reachable closure, which is EXP-007 and has not run on the 5×3. The
  column is reported as absent rather than estimated.

    pypy scripts/exp004_compressibility.py --arm h2
    pypy scripts/exp004_compressibility.py --arm h2 --block-size 8192
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fliphex.variant import Arm, Variant  # noqa: E402
from solver.checkpoint import Checkpoint, atomic_write  # noqa: E402
from solver.sweep_reader import SweepReader  # noqa: E402

try:  # The registered encoding is block-Zstd.
    import zstandard
except ImportError:  # pragma: no cover - optional dependency
    zstandard = None


def rle_block(block: bytes) -> int:
    """Bytes a byte-level RLE would need for one block.

    Two bytes per run — value and count, counts capped at 255. Deliberately the
    simplest scheme that answers the question the experiment asks: whether equal
    values sit next to each other in index order.
    """
    if not block:
        return 0
    runs = 1
    length = 1
    previous = block[0]
    for byte in block[1:]:
        if byte == previous and length < 255:
            length += 1
        else:
            runs += 1
            length = 1
            previous = byte
    return runs * 2


def profile_layer(values: bytearray, block_size: int, compressor) -> dict:
    raw = len(values)
    rle = zstd = 0
    blocks = 0
    for offset in range(0, raw, block_size):
        block = bytes(values[offset : offset + block_size])
        blocks += 1
        rle += rle_block(block)
        if compressor is not None:
            zstd += len(compressor.compress(block))
    return {
        "raw_bytes": raw,
        "rle_bytes": rle,
        "zstd_bytes": zstd if compressor is not None else None,
        "blocks": blocks,
        "block_size": block_size,
    }


def run(args) -> dict:
    variant = Variant(args.board[0], args.board[1], Arm(args.arm))
    reader = SweepReader(variant, Checkpoint(args.checkpoint / variant.name))

    # The registration names block-Zstd. `zstandard` is installed in neither
    # interpreter here, so zlib stands in — recorded as a substitution rather
    # than reported as if it were the registered encoding. Both answer the same
    # question (what a general-purpose coder gets on one independently
    # decodable block); their ratios differ by a few percent at these sizes,
    # which is far below anything this measurement would turn on.
    if zstandard is not None:
        compressor = zstandard.ZstdCompressor(level=args.zstd_level)
        coder = f"zstd level {args.zstd_level}"
    else:
        import zlib

        compressor = type(
            "ZlibShim",
            (),
            {
                "compress": staticmethod(
                    lambda data: zlib.compress(data, args.zstd_level)
                )
            },
        )()
        coder = f"zlib level {args.zstd_level} (SUBSTITUTE — zstandard absent)"

    print(f"\n  === EXP-004 — compressibility, {variant.name} ===")
    print(
        f"  block size {args.block_size:,} bytes "
        f"({4 * args.block_size:,} positions per probe)"
    )
    print(f"  general-purpose coder: {coder}")
    print(
        f"  interpreter: {sys.implementation.name} {sys.version.split()[0]}\n",
        flush=True,
    )

    started = time.perf_counter()
    rows = []
    print(
        f"  {'t':>3} {'raw MB':>10} {'RLE MB':>10} {'RLE x':>7} "
        f"{'zstd MB':>10} {'zstd x':>7}"
    )
    for t in range(variant.n_cells + 1):
        row = profile_layer(reader.layer(t), args.block_size, compressor)
        row["layer"] = t
        rows.append(row)
        mb = 1024 * 1024
        zstd_mb = (
            f"{row['zstd_bytes'] / mb:10.2f}" if row["zstd_bytes"] else "         -"
        )
        zstd_x = (
            f"{row['raw_bytes'] / row['zstd_bytes']:7.2f}"
            if row["zstd_bytes"]
            else "      -"
        )
        print(
            f"  {t:>3} {row['raw_bytes'] / mb:10.2f} {row['rle_bytes'] / mb:10.2f} "
            f"{row['raw_bytes'] / max(row['rle_bytes'], 1):7.2f} {zstd_mb} {zstd_x}",
            flush=True,
        )
        reader.release()

    elapsed = time.perf_counter() - started
    raw = sum(r["raw_bytes"] for r in rows)
    rle = sum(r["rle_bytes"] for r in rows)
    zstd = sum(r["zstd_bytes"] or 0 for r in rows) if compressor else None

    print()
    print(
        f"    raw ................... {raw / 1024**3:.2f} GiB "
        f"({8 * raw / sum(4 * r['raw_bytes'] for r in rows):.2f} bits/position)"
    )
    print(f"    block-RLE ............. {rle / 1024**3:.2f} GiB ({raw / rle:.2f}x)")
    if zstd:
        print(
            f"    block-Zstd ............ {zstd / 1024**3:.2f} GiB ({raw / zstd:.2f}x)"
        )
    print(
        "    logic-minimised ....... ABSENT — needs the reachable closure, "
        "which is EXP-007 and has not run on the 5x3"
    )
    print(f"    elapsed ............... {elapsed:,.1f}s\n", flush=True)

    positions = sum(4 * r["raw_bytes"] for r in rows)
    return {
        "experiment": "EXP-004",
        "variant": variant.name,
        "block_size": args.block_size,
        "coder": coder,
        "zstd_level": args.zstd_level,
        "interpreter": f"{sys.implementation.name} {sys.version.split()[0]}",
        "layers": rows,
        "raw_bytes": raw,
        "rle_bytes": rle,
        "zstd_bytes": zstd,
        "coder_is_registered_zstd": zstandard is not None,
        "positions": positions,
        "raw_bits_per_position": 8 * raw / positions,
        "rle_ratio": raw / rle,
        "zstd_ratio": raw / zstd if zstd else None,
        "logic_minimised": None,
        "logic_minimised_note": (
            "absent: needs the reachable closure (EXP-007), not run on the 5x3"
        ),
        "seconds": elapsed,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--board", type=int, nargs=2, default=[5, 3], metavar=("COLS", "ROWS")
    )
    p.add_argument("--arm", choices=["h1", "h2"], default="h2")
    p.add_argument("--checkpoint", type=Path, default=Path("data/checkpoints"))
    p.add_argument(
        "--block-size",
        type=int,
        default=4096,
        help="bytes per independently decodable block; a probe touches one",
    )
    p.add_argument("--zstd-level", type=int, default=3)
    p.add_argument("--out", type=Path, default=Path("results"))
    p.add_argument("--no-write", action="store_true")
    args = p.parse_args()

    artefact = run(args)

    if not args.no_write:
        path = args.out / f"exp004-compressibility-{args.board[0]}x{args.board[1]}.json"
        atomic_write(path, json.dumps(artefact, indent=2).encode())
        print(f"    artefact -> {path}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
