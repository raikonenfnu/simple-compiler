import sys
import json
from dataclasses import dataclass
from cfg import get_cfg, form_blocks, flatten_named_blocks

DCE_SKIP_OPS = {"jmp"}
NO_SSA_OP = {"br", "ret", "print"}

# Helper function to represent every op/value in
# a unique way.
@dataclass
class SSA:
    dest: str
    local_id: int
    block_id: str

    def __hash__(self):
        return hash(self.dest) ^ hash(self.local_id) ^ hash(self.block_id)

# Explore blocks by walking down CFG in a BFS manner.
# in every block, we go down each instructions and
# add dependency information.
# We treat every block -> succ relation as a new worklist
# to represent that instruction/value from previous block
# may impact their succesor blocks.
# TODO: Currently this method only represent a 1-step
#       relation between block, we need to make it fully
#       global for completeness.
def get_consumers(func, cfg, named_blocks):
    consumers = {}
    last_def = {}

    # Build consumer map for fn args.
    if "args" in func:
        for arg in func["args"]:
            arg_ssa = SSA(arg["name"], 0, 0)
            last_def[arg["name"]] = [0, 0]
            consumers[arg_ssa] = []

    # Build consumer map for body.
    # next(iter(dict)) method gets the first key of dict.
    worklist = [next(iter(cfg))]
    visited = set()
    prev_id = "none"
    while len(worklist) > 0:
        block_id = worklist.pop(0)
        visited.add(prev_id + "->" + block_id)
        for instr_id, instr in enumerate(named_blocks[block_id]):
            if "op" not in instr:
                continue
            if instr["op"] in DCE_SKIP_OPS:
                continue
            if "dest" not in instr and instr["op"] not in NO_SSA_OP:
                continue
            dst_name = instr["dest"] if "dest" in instr else instr["op"]
            last_def[dst_name] = [instr_id, block_id]
            new_ssa = SSA(dst_name, instr_id, block_id)
            consumers[new_ssa] = []
            if "args" in instr:
                for arg in instr["args"]:
                    consumers[SSA(arg, last_def[arg][0], last_def[arg][1])].append(new_ssa)
        for succ in cfg[block_id]:
            if block_id + "->" + succ in visited:
                continue
            worklist.append(succ)
        prev_id = block_id
    return consumers

def dce(named_blocks, consumers):
    for block_id in named_blocks:
        offset = 0
        new_block = named_blocks[block_id].copy()
        for instr_id, instr in enumerate(named_blocks[block_id]):
            if "dest" not in instr:
                continue
            if SSA(instr["dest"], instr_id, block_id) not in consumers:
                continue
            if len(consumers[SSA(instr["dest"], instr_id, block_id)]) == 0:
                new_block.pop(instr_id - offset)
                offset += 1
        named_blocks[block_id] = new_block

def main():
    prog = json.load(sys.stdin)
    for func_id, func in enumerate(prog["functions"]):
        fn_blocks = form_blocks(func["instrs"])
        cfg, named_blocks = get_cfg(fn_blocks)
        consumers = get_consumers(func, cfg, named_blocks)
        dce(named_blocks, consumers)
        prog["functions"][func_id]["instrs"] = flatten_named_blocks(named_blocks)
    json.dump(prog, sys.stdout, indent=2, sort_keys=True)


if __name__ == "__main__":
    main()