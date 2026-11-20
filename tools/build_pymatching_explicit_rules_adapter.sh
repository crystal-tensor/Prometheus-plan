#!/bin/sh
set -eu

if [ "$#" -ne 2 ]; then
    echo "usage: $0 PYMatching-source-dir wheel-output-dir" >&2
    exit 2
fi

source_dir=$1
wheel_dir=$2
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
patch_file="$script_dir/patches/pymatching_v2.4.0_explicit_rules.patch"
expected_commit=6f63b2b9474ba0fa7e511fe52bffdce858a06984

actual_commit=$(git -C "$source_dir" rev-parse HEAD)
if [ "$actual_commit" != "$expected_commit" ]; then
    echo "expected PyMatching $expected_commit, got $actual_commit" >&2
    exit 1
fi

git -C "$source_dir" apply --check "$patch_file"
git -C "$source_dir" apply "$patch_file"
mkdir -p "$wheel_dir"
python3 -m pip wheel --no-deps --wheel-dir "$wheel_dir" "$source_dir"
