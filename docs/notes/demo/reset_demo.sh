#!/usr/bin/env bash
# Reset the demo's workspace and load the four model specs again (docs/notes/demo_mcp.md §1, "To start the demo
# again from nothing"; record 0087's demo root). A note's helper, not part of EMA.
#
#   docs/notes/demo/reset_demo.sh            # move ema_workspace/ and exports/ aside, with a timestamp
#   docs/notes/demo/reset_demo.sh --delete   # delete them instead
#
# EMA_REPO and EMA_DEMO override the repository and the demo root. The model directories (beam/, borehole/,
# ishigami/, r5/) are left as they are; §1 makes them. Loading asks nothing and runs nothing (W1).
set -euo pipefail

EMA=${EMA_REPO:-/Users/paulconstantine/PycharmProjects/EMA}
DEMO=${EMA_DEMO:-/Users/paulconstantine/ema_demo}
SPECS=(ishigami/model.json borehole/model.json r5/model.json beam/beam.json)

delete=false
case "${1:-}" in
    "") ;;
    --delete) delete=true ;;
    *) echo "usage: $0 [--delete]" >&2; exit 2 ;;
esac

[[ -d "$DEMO" ]] || { echo "no demo root at $DEMO; make it with demo_mcp.md §1" >&2; exit 1; }
for spec in "${SPECS[@]}"; do
    [[ -f "$DEMO/$spec" ]] || { echo "missing $DEMO/$spec; copy it with demo_mcp.md §1" >&2; exit 1; }
done

# A server or Python session with the workspace open would keep writing to the old ema.db: stop it first.
if [[ -f "$DEMO/ema_workspace/ema.db" ]] && pids=$(lsof -t "$DEMO/ema_workspace/ema.db" 2>/dev/null); then
    echo "the workspace is open in process(es) $(echo $pids | tr '\n' ' ')(an MCP server or a Python session);" \
         "close it and run this again" >&2
    exit 1
fi

stamp=$(date +%Y%m%d-%H%M%S)
for dir in ema_workspace exports; do
    [[ -e "$DEMO/$dir" ]] || continue
    if $delete; then
        rm -rf "${DEMO:?}/$dir"
        echo "deleted $DEMO/$dir"
    else
        mv "$DEMO/$dir" "$DEMO/$dir.$stamp"
        echo "moved $DEMO/$dir to $DEMO/$dir.$stamp"
    fi
done

cd "$DEMO"
uv run --project "$EMA" python - "$DEMO" "${SPECS[@]}" <<'EOF'
import sys
import ema

root, specs = sys.argv[1], sys.argv[2:]
with ema.open_workspace("ema_workspace", root=root) as ws:
    for spec in specs:
        print(ws.load_model(spec))
    print()
    for model in ws.list_models():
        print(model)
EOF
