import logging

from pynvim import Nvim

logger = logging.getLogger(__name__)


def len_pending_messages(nvim: Nvim):
    return len(nvim._session._pending_messages)


def receive_message(nvim: Nvim):
    event = nvim.next_message()

    # This value is not strictly accurate.
    # It is correct most of the time, but when you send too many messages at once (e.g. change visual selection using mouse) it can be wrong (smaller than the actual number)
    # It is only here to detect bloated state (too many messages)
    nvim.vars["jupynium_num_pending_msgs"] = max(
        nvim.vars.get("jupynium_num_pending_msgs", 0) - 1, 0
    )

    return event


def receive_all_pending_messages(nvim: Nvim):
    """
    It doesn't guarantee to grab all messages that are previously sent. Maybe the last one or two may still be in process.
    """
    events = []
    while len_pending_messages(nvim) > 0:
        events.append(receive_message(nvim))

    return events


"""
def event_to_dict(event):
    event_dict = {}
    if event is None:
        logger.error("event is None")
        return event_dict

    event_dict["type"] = event[0]  # request / notification
    if event[0] == "request":
        event_dict["request"] = event[3]

    # on_bytes / on_bytes_remove, CursorMoved, CursorMovedI, visual_enter, visual_leave, grab_entire_buf, VimLeave
    event_dict["name"] = event[1]
    event_args = {}

    if event[1] == "start_sync":
        (
            _,
            event_args["filename"],
            event_args["content"],
        ) = event[2]
    elif event[1] in [
        "stop_sync",
        "save_ipynb",
        "toggle_selected_cells_output_scroll",
        "execute_selected_cells",
        "clear_selected_cells_outputs",
        "VimLeavePre",
        "BufWinLeave",
    ]:
        pass
    elif event[1] == "on_lines":
        (
            _,
            event_args["lines"],
            event_args["start_row"],
            event_args["old_end_row"],
            event_args["new_end_row"],
            event_args["old_byte_size"],
        ) = event[2]
    elif event[1] == "scroll_ipynb":
        (
            _,
            event_args["scroll"],
        ) = event[2]
    elif event[1] == "download_ipynb":
        (
            _,
            event_args["buf_filepath"],
            event_args["filename"],
        ) = event[2]

        assert event_args["buf_filepath"] != ""
    elif event[1] == "scroll_to_cell":
        (
            _,
            event_args["cursor_pos_row"],
        ) = event[2]
    elif event[1] in ["CursorMoved", "CursorMovedI", "visual_enter", "visual_leave"]:
        (
            _,
            event_args["cursor_pos_row"],
            event_args["visual_start_row"],
        ) = event[2]
    elif event[1] == "grab_entire_buf":
        (
            _,
            event_args["content"],
        ) = event[2]

    event_dict["bufnr"] = event[2][0]
    event_dict["args"] = event_args
    return event_dict


def events_to_listdict(events):
    return [event_to_dict(event) for event in events]
"""
