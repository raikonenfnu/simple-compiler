import sys
import json

TERMINATORS = {"jmp", "br", "ret"}

# Within a CFG, jumps and branch can only happen at
# end of basic block, and you can only jump to a
# top of basic block.
def form_blocks(body):
    blocks = []
    cur_block = []
    for instr_id, instr in enumerate(body):
        if "op" in instr:
            cur_block.append(instr)

            if instr["op"] in TERMINATORS:
                blocks.append(cur_block)
                cur_block = []

        elif "label" in instr:
            blocks.append(cur_block)
            cur_block = [instr]
        else:
            raise ValueError(f"Encountered unexpected intruction type. {instr}")

        # Append final block if reach end of function.
        if instr_id == len(body) - 1:
            blocks.append(cur_block)

    return blocks

def get_cfg(blocks):
    cfg = {}
    previous_block_name = ""
    for block_id, block in enumerate(blocks):
        block_name = f"bb{block_id}"
        succ = {}
        if "label" in block[0]:
            block_name = block[0]["label"]
        if "op" not in block[-1]:
            raise ValueError("Expected last instr in a block to be an op.")
        if block[-1]["op"] in {"jmp", "br"}:
            succ = block[-1]["labels"]
        # Handle case where previous block do not branch out.
        # this allow us to safely generate cfg and name blocks
        # on the fly.
        if previous_block_name in cfg and len(cfg[previous_block_name]) == 0:
            cfg[previous_block_name] = [block_name]
        cfg[block_name] = succ
        previous_block_name = block_name
    return cfg

def cfg_printer(fn_name, cfg):
    print(f"digraph {fn_name}")
    for block_id in cfg:
        print(f"  {block_id};")
    for block_id in cfg:
        for succ in cfg[block_id]:
            print("  {block_id} -> {succ};")
    print("}")
def main():
    prog = json.load(sys.stdin)
    for func in prog["functions"]:
        fn_blocks = form_blocks(func["instrs"])
        cfg = get_cfg(fn_blocks)
        cfg_printer(func["name"],cfg)



if __name__ == "__main__":
    main()