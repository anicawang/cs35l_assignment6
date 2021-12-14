import os
import sys
import zlib
import copy
from collections import deque

class CommitNode:
    def __init__(self, commit_hash):
        self.commit_hash = commit_hash
        self.parents = set()
        self.children = set()

def get_git_directory():
    dir = os.getcwd()
    while dir != "/":
        if os.path.exists(dir + "/.git"):
            return (dir + "/.git")
        dir = os.path.dirname(dir)
    sys.exit("Not inside Git repository\n")

def get_local_branch_names(path, branches, past):
    local_branch_heads = set()
    list_of_files = os.listdir(path)
    for entry in list_of_files:
        full_path = os.path.join(path, entry)
        if os.path.isdir(full_path):
            get_local_branch_names(full_path, branches, past=entry)
        else:
            with open(full_path, "r") as myfile:
                commit = myfile.read().strip("\n")
                if past != "":
                    branchname = past + "/" + entry
                else:
                    branchname = entry
                if commit not in branches:
                    branches[commit] = [branchname]
                else:
                    branches[commit].append(branchname)
                local_branch_heads.add(commit)
    return branches, local_branch_heads

def build_graph(path, local_branch_heads):
    commit_nodes = {}
    visited = set()
    stack = sorted(local_branch_heads)
    while stack:
        commit_hash = stack.pop()
        if commit_hash in visited:
            continue
        visited.add(commit_hash)
        if commit_hash not in commit_nodes:
            commit_nodes[commit_hash] = CommitNode(commit_hash)
        commit = commit_nodes[commit_hash]
        comp = open(path + "/objects/" + commit_hash[:2]
                               + "/" + commit_hash[2:], 'rb').read()
        decomp = zlib.decompress(comp).decode()
        for line in decomp.split("\n"):
            if line.startswith('parent'):
                parenthash = line.split(" ")[1]
                commit.parents.add(parenthash)
        for p in commit.parents:
            if p not in visited:
                stack.append(p)
            if p not in commit_nodes:
                commit_nodes[p] = CommitNode(p)
            commit_nodes[p].children.add(commit_hash)
    return commit_nodes

def topological_sort(commit_nodes):
    result = []
    no_children = deque()
    copy_graph = copy.deepcopy(commit_nodes)
    for commit_hash in copy_graph:
        if len(copy_graph[commit_hash].children) == 0:
            no_children.append(commit_hash)
    while len(no_children) > 0:
        commit_hash = no_children.popleft()
        result.append(commit_hash)
        for parent_hash in list(copy_graph[commit_hash].parents):
            copy_graph[commit_hash].parents.remove(parent_hash)
            copy_graph[parent_hash].children.remove(commit_hash)
            if len(copy_graph[parent_hash].children) == 0:
                no_children.append(parent_hash)
    if len(result) < len(commit_nodes):
        raise Exception("cycle detected")
    return result

def print_topo_commits(commit_nodes, topo_commits, head_to_branches):
    jumped = False
    for i in range(len(topo_commits)):
        commit_hash = topo_commits[i]
        if jumped:
            jumped = False
            sticky_hash = ' '.join(commit_nodes[commit_hash].children)
            print(f'={sticky_hash}')
        branches = sorted(head_to_branches[commit_hash]) if commit_hash in head_to_branches else []
        print(commit_hash + (' ' + ' '.join(branches) if branches else ''))
        if i + 1 < len(topo_commits) and topo_commits[i+1] not in commit_nodes[commit_hash].parents:
            jumped = True
            sticky_hash = ' '.join(commit_nodes[commit_hash].parents)
            print(f'{sticky_hash}=\n')

def topo_order_commits():
    dir = get_git_directory()
    branches, local_branch_heads = get_local_branch_names(dir + "/refs/heads", {}, "")
    commit_nodes = build_graph(dir, local_branch_heads)
    result = topological_sort(commit_nodes)
    print_topo_commits(commit_nodes, result, branches)

if __name__ == '__main__':
    topo_order_commits()
