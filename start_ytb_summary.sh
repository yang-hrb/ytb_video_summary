#!/bin/bash

SESSION_NAME="ytb_summary"

# Check if session exists
tmux has-session -t $SESSION_NAME 2>/dev/null

if [ $? != 0 ]; then
    echo "Creating new tmux session: $SESSION_NAME"
    tmux new-session -s $SESSION_NAME
else
    echo "Attaching to existing tmux session: $SESSION_NAME"
    tmux attach-session -t $SESSION_NAME
fi