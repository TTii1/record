#!/usr/bin/env bash
# ============================================================
# 大文件拆分 / 拼接工具
#
# 用途：
#   把大压缩包拆成多个不超过指定大小的分块，分块统一以 .deb 结尾
#   （公司下载限制只允许 .deb 后缀），在目标机器上运行 join 模式
#   即可无损拼回原文件。
#
# 用法：
#   拆分:  split_join.sh split <文件> [分块大小]
#   拼接:  split_join.sh join <输出文件> [分块1 分块2 ...]
#
# 说明：
#   - 大小支持 K/M/G 单位，按十进制计算（1M = 1,000,000 字节），
#     确保分块严格不超过指定大小
#   - 拆分产物命名: <原文件名>.001.deb、.002.deb ...
#   - join 不传分块时，自动拼接当前目录下所有 *.deb
# ============================================================
set -euo pipefail

DEFAULT_SIZE="500M"

usage() {
    cat <<EOF
用法:
  $0 split <文件> [分块大小]
      按指定大小拆分文件（默认 ${DEFAULT_SIZE}，支持 K/M/G，十进制）。
      产物: <文件名>.001.deb、<文件名>.002.deb ...

  $0 join <输出文件> [分块1 分块2 ...]
      把分块拼回原文件。不提供分块时，自动拼接当前目录下所有 *.deb。
      分块顺序按编号自动排序，无需按顺序传入。

示例:
  $0 split record_free.tar.gz            # 每块 ≤ 500M
  $0 split record_free.tar.gz 100M       # 每块 ≤ 100M
  $0 join record_free.tar.gz *.deb       # 指定分块
  $0 join record_free.tar.gz             # 自动找当前目录所有 *.deb
EOF
}

# 大小转字节: 500M -> 500000000（十进制）
to_bytes() {
    local v="$1" num
    case "${v: -1}" in
        K|k) num=${v%[Kk]}; echo $((num * 1000)) ;;
        M|m) num=${v%[Mm]}; echo $((num * 1000000)) ;;
        G|g) num=${v%[Gg]}; echo $((num * 1000000000)) ;;
        *)   echo "$v" ;;
    esac
}

# 从分块文件名提取编号: record_free.tar.gz.001.deb -> 1
part_num() {
    local n
    n=$(basename "$1" .deb | grep -oE '[0-9]+$' || true)
    if [ -z "$n" ]; then echo "0"; else echo "$((10#$n))"; fi
}

cmd_split() {
    local file="$1" size="${2:-$DEFAULT_SIZE}"
    local dir base bytes
    [ -f "$file" ] || { echo "错误: 文件不存在: $file" >&2; exit 1; }
    dir=$(dirname "$file")
    base=$(basename "$file")
    bytes=$(to_bytes "$size")

    echo "拆分 $file（每块 ≤ $size = $bytes 字节）..."
    (cd "$dir" && split -b "$bytes" -d -a 3 "$base" "${base}.")

    shopt -s nullglob
    local n=0 p
    for p in "$dir/${base}".???; do
        # 只处理 split 生成的数字后缀，避免误改其他文件
        [[ "$p" =~ \.[0-9]{3}$ ]] || continue
        mv "$p" "${p}.deb"
        n=$((n + 1))
    done
    echo "完成: 共 $n 个分块"
    ls -lh "$dir/${base}".*.deb
    echo
    echo "拼接方法: $0 join '$file' '$dir/${base}'.*.deb"
}

cmd_join() {
    local out="$1"; shift || true
    local parts=() sorted p sum=0 osize
    if [ "$#" -gt 0 ]; then
        parts=("$@")
    else
        shopt -s nullglob
        parts=(./*.deb)
        [ "${#parts[@]}" -gt 0 ] || { echo "错误: 未指定分块，且当前目录没有 .deb 文件" >&2; exit 1; }
    fi

    # 按编号排序
    sorted=$(for p in "${parts[@]}"; do
                 printf '%d %s\n' "$(part_num "$p")" "$p"
             done | sort -n | cut -d' ' -f2-)
    [ -n "$sorted" ] || { echo "错误: 没有可拼接的分块" >&2; exit 1; }

    echo "拼接顺序:"
    local i=1
    for p in $sorted; do
        echo "  $i) $p"
        sum=$((sum + $(stat -c%s "$p")))
        i=$((i + 1))
    done

    : > "$out"
    for p in $sorted; do
        cat "$p" >> "$out"
    done

    osize=$(stat -c%s "$out")
    echo "拼接完成: $out（$osize 字节）"
    if [ "$sum" -eq "$osize" ]; then
        echo "✓ 大小校验通过（分块总和 = 输出）"
    else
        echo "✗ 警告: 输出大小 $osize 与分块总和 $sum 不一致！" >&2
    fi
    if file "$out" | grep -q gzip; then
        if gzip -t "$out" 2>/dev/null; then
            echo "✓ gzip 完整性校验通过"
        else
            echo "✗ gzip 完整性校验失败！" >&2
        fi
    fi
}

cmd="${1:-}"
shift || true
case "$cmd" in
    split) cmd_split "$@" ;;
    join)  cmd_join "$@" ;;
    -h|--help|help|"") usage ;;
    *) echo "错误: 未知命令 $cmd" >&2; usage; exit 1 ;;
esac
