import time

from pynvim import Nvim

from jupynium.rpc_messages import receive_all_pending_messages, receive_message


def test_event_default_variables(nvim_1: Nvim):
    assert nvim_1.vars["jupynium_channel_id"] > 0
    assert nvim_1.vars["jupynium_num_pending_msgs"] == 0


def test_event_before_start_sync(nvim_1: Nvim):
    nvim_1.feedkeys(nvim_1.replace_termcodes("<esc>", True, True, True))
    nvim_1.feedkeys("i# %%\nabc")
    nvim_1.feedkeys(nvim_1.replace_termcodes("<esc>", True, True, True))
    assert nvim_1.vars["jupynium_num_pending_msgs"] == 0


def test_event_start_sync_cancel(nvim_1: Nvim):
    nvim_1.lua.Jupynium_start_sync(async_=True)
    assert nvim_1.vars["jupynium_num_pending_msgs"] == 1
    event = receive_message(nvim_1)
    assert event is not None
    assert event[0] == "request"
    assert event[1] == "start_sync"

    event[3].send("N")  # Not OK is cancel
    nvim_1.feedkeys(nvim_1.replace_termcodes("<esc>", True, True, True))
    nvim_1.feedkeys("i# %%\nabc")
    nvim_1.feedkeys(nvim_1.replace_termcodes("<esc>", True, True, True))
    assert nvim_1.vars["jupynium_num_pending_msgs"] == 0


def test_event_start_sync(nvim_1: Nvim):
    nvim_1.lua.Jupynium_start_sync(async_=True)
    assert nvim_1.vars["jupynium_num_pending_msgs"] == 1
    event = receive_message(nvim_1)
    assert event is not None
    assert event[0] == "request"
    assert event[1] == "start_sync"

    event[3].send("OK")  # Not OK is cancel
    nvim_1.feedkeys(nvim_1.replace_termcodes("<esc>", True, True, True))
    nvim_1.feedkeys("i# %%\nabc")
    nvim_1.feedkeys(nvim_1.replace_termcodes("<esc>", True, True, True))

    assert nvim_1.vars["jupynium_num_pending_msgs"] > 0

    count_cursormoved_i = 0

    time.sleep(0.5)
    events = receive_all_pending_messages(nvim_1)
    for event in events:
        if event[0] == "notification" and event[1] == "CursorMovedI":
            count_cursormoved_i += 1

    assert (
        count_cursormoved_i > 0
    )  # CursorMovedI should be triggered. I think it gets triggered only once after the feedkeys call


def test_event_stop_sync(nvim_1: Nvim):
    nvim_1.lua.Jupynium_stop_sync(async_=True)
    assert nvim_1.vars["jupynium_num_pending_msgs"] == 1
    event = receive_message(nvim_1)
    assert event is not None
    assert event[0] == "notification"
    assert event[1] == "stop_sync"

    nvim_1.feedkeys(nvim_1.replace_termcodes("<esc>", True, True, True))
    nvim_1.feedkeys("i# %%\nabc")
    nvim_1.feedkeys(nvim_1.replace_termcodes("<esc>", True, True, True))

    assert nvim_1.vars["jupynium_num_pending_msgs"] == 0
