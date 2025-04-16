
import logging
from meshagent.tools import Toolkit, Tool

import mcp
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
import copy

from .cleanup import replace_optional_parameters, cleanup

logger = logging.getLogger("mcp")

def make_strict_schema(schema: dict):
    cleanup(schema, True)
    return schema


class MCPTool(Tool):
    def __init__(self, *, session: mcp.ClientSession, mcp_tool: mcp.Tool):
        self.mcp_tool = mcp_tool
        self.session = session
        input_schema = mcp_tool.inputSchema
        super().__init__(name=mcp_tool.name, input_schema=make_strict_schema(input_schema), title=mcp_tool.name, description=mcp_tool.description)

    async def execute(self, context, **kwargs):
        arguments = replace_optional_parameters(copy.deepcopy(kwargs))      
        result = await self.session.call_tool(self.mcp_tool.name, arguments)
        return result.model_dump_json()

class MCPToolkit(Toolkit):
    def __init__(self, *, name: str, url: str):
        
        self._url = url
        self._ctx = sse_client(self._url)
        self._session = None
        super().__init__(name=name, tools=[])

    async def __aenter__(self) -> 'MCPToolkit':        
        read_stream, write_stream = await self._ctx.__aenter__()
        self._session_ctx = ClientSession(read_stream=read_stream, write_stream=write_stream)
        self._session = await self._session_ctx.__aenter__()

        mcp_tools = await self._session.list_tools()
        for tool in mcp_tools.tools:
            self.tools.append(MCPTool(session=self._session, mcp_tool=tool))

        return self
    
    async def __aexit__(self, exec_type, exec, tb):
        await self._session_ctx.__aexit__(exec_type, exec, tb)
        await self._ctx.__aexit__(exec_type, exec, tb)
        return None

    

