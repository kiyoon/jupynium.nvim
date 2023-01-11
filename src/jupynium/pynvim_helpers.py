import logging
import time

from pkg_resources import resource_stream
import pynvim

logger = logging.getLogger(__name__)


def attach_and_init(nvim_listen_addr):
    logger.info("nvim addr: %s", nvim_listen_addr)
    for _ in range(30):
        try:
            if ":" in nvim_listen_addr:
                host, port = nvim_listen_addr.split(":")
                nvim = pynvim.attach(
                    "tcp",
                    address=host,
                    port=int(port),
                )
            else:
                nvim = pynvim.attach("socket", path=nvim_listen_addr)
        except Exception:
            time.sleep(0.1)
        else:
            break
    else:
        raise TimeoutError("Timeout while waiting for nvim to start")

    logger.info("nvim attached")

    # existing_channel_id = nvim.vars.get("jupynium_channel_id", None)
    # if existing_channel_id is None:
    logger.info("Initialising..")
    logger.info(f"Communicating with {nvim.channel_id = }")
    nvim.vars["jupynium_channel_id"] = nvim.channel_id
    nvim.vars["jupynium_num_pending_msgs"] = 0
    # Define helper functions
    # Must come at the beginning
    lua_code = resource_stream("jupynium", "lua/defaults.lua").read().decode("utf-8")
    nvim.exec_lua(lua_code)

    lua_code = resource_stream("jupynium", "lua/helpers.lua").read().decode("utf-8")
    nvim.exec_lua(lua_code)

    lua_code = resource_stream("jupynium", "lua/notify.lua").read().decode("utf-8")
    nvim.exec_lua(lua_code)

    # keymaps
    lua_code = resource_stream("jupynium", "lua/commands.lua").read().decode("utf-8")
    nvim.exec_lua(lua_code)
    lua_code = resource_stream("jupynium", "lua/keymaps.lua").read().decode("utf-8")
    nvim.exec_lua(lua_code)

    lua_code = (
        resource_stream("jupynium", "lua/autocmd_vimleave.lua").read().decode("utf-8")
    )
    nvim.exec_lua(lua_code)

    nvim.lua.Jupynium_notify.info(
        [
            "Jupynium sucessfully attached and initialised.",
            "Run `:JupyniumStartSync`",
        ],
        async_=True,
    )

    # There is no need for below, as Jupynium already checks if it's running already.
    # Only be useful if multiple computers try to attach to the same nvim
    # However, Jupynium can exit unexpectedly so checking the variable is
    # not the most stable way to check if it's running..

    # elif existing_channel_id < 0:
    #     logger.info("Jupynium already initialised on nvim, but has exited before.")
    #     logger.info("Just changing the channel ID and buffer")
    #     nvim.lua.Jupynium_notify.info(
    #         [
    #             "Jupynium sucessfully attached and initialised.",
    #             "Run `:JupyniumStartSync`",
    #         ],
    #         async_=True,
    #     )
    #     # Already initialised, but exited once
    #     nvim.vars["jupynium_channel_id"] = nvim.channel_id
    #     nvim.vars["jupynium_num_pending_msgs"] = 0
    # else:
    #     nvim.lua.Jupynium_notify.error(
    #         ["Jupynium already running on another side.", "Failed to initialise."],
    #         async_=True,
    #     )
    #     raise Exception("Jupynium already running on another side. Exiting..")

    return nvim
