import time
import uuid

from open_webui.internal.db import get_async_db
from open_webui.models.base import Base

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Integer, JSON, select, String, Text
from sqlalchemy.orm import Mapped, mapped_column

####################
# MCP Server DB Schema
####################


class MCPServer(Base):
    __tablename__ = "mcp_server"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    server_type = mapped_column(
        String, default="user_created"
    )  # "built_in" or "user_created"
    command: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )  # JSON string for command array
    args = mapped_column(JSON, nullable=True, default=[])  # Command arguments
    env = mapped_column(JSON, nullable=True, default={})  # Environment variables
    transport: Mapped[str] = mapped_column(String, default="stdio")  # "stdio" or "http"
    url: Mapped[str] = mapped_column(String, nullable=True)  # For HTTP transport
    port = mapped_column(Integer, nullable=True)  # For HTTP transport
    is_active = mapped_column(Boolean, default=True)
    is_deletable = mapped_column(Boolean, default=True)
    capabilities = mapped_column(JSON, nullable=True, default={})
    tools = mapped_column(JSON, nullable=True, default=[])
    access_control: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[int] = mapped_column(BigInteger)
    updated_at: Mapped[int] = mapped_column(BigInteger)


class MCPServerModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None = None
    name: str
    description: str | None = None
    server_type: str = "user_created"
    command: str | None = None
    args: list | None = []
    env: dict | None = {}
    transport: str = "stdio"
    url: str | None = None
    port: int | None = None
    is_active: bool = True
    is_deletable: bool = True
    capabilities: dict | None = {}
    tools: list | None = []
    access_control: dict | None = None
    created_at: int
    updated_at: int


####################
# Forms
####################


class MCPServerForm(BaseModel):
    name: str
    description: str | None = None
    server_type: str = "user_created"
    command: str | None = None
    args: list | None = []
    env: dict | None = {}
    transport: str = "stdio"
    url: str | None = None
    port: int | None = None
    is_active: bool = True
    is_deletable: bool = True
    capabilities: dict | None = {}
    tools: list | None = []
    access_control: dict | None = None


class MCPServerTable:
    async def insert_new_server(
        self,
        name: str,
        description: str = None,
        user_id: str = None,
        server_type: str = "user_created",
        command: str = None,
        args: list = None,
        env: dict = None,
        transport: str = "stdio",
        url: str = None,
        port: int = None,
        is_active: bool = True,
        is_deletable: bool = True,
        capabilities: dict = None,
        tools: list = None,
        access_control: dict = None,
    ) -> MCPServerModel | None:
        if args is None:
            args = []
        if env is None:
            env = {}
        if capabilities is None:
            capabilities = {}
        if tools is None:
            tools = []

        server_id = str(uuid.uuid4())

        try:
            async with get_async_db() as db:
                server = MCPServerModel(
                    **{
                        "id": server_id,
                        "user_id": user_id,
                        "name": name,
                        "description": description,
                        "server_type": server_type,
                        "command": command,
                        "args": args,
                        "env": env,
                        "transport": transport,
                        "url": url,
                        "port": port,
                        "is_active": is_active,
                        "is_deletable": is_deletable,
                        "capabilities": capabilities,
                        "tools": tools,
                        "access_control": access_control,
                        "created_at": int(time.time()),
                        "updated_at": int(time.time()),
                    }
                )

                result = MCPServer(**server.model_dump())
                db.add(result)
                await db.commit()
                await db.refresh(result)

                if result:
                    return MCPServerModel.model_validate(result)
                else:
                    return None
        except Exception as e:
            print(f"Error creating MCP server: {e}")
            return None

    async def get_server_by_id(self, id: str) -> MCPServerModel | None:
        try:
            async with get_async_db() as db:
                server = await db.get(MCPServer, id)
                return MCPServerModel.model_validate(server) if server else None
        except Exception as e:
            print(f"Error getting MCP server by id: {e}")
            return None

    async def get_server_by_name(self, name: str) -> MCPServerModel | None:
        try:
            async with get_async_db() as db:
                server = await db.scalar(
                    select(MCPServer).where(MCPServer.name == name)
                )
                return MCPServerModel.model_validate(server) if server else None
        except Exception as e:
            print(f"Error getting MCP server by name: {e}")
            return None

    async def get_servers(self, user_id: str | None = None) -> list[MCPServerModel]:
        try:
            async with get_async_db() as db:
                query = select(MCPServer)
                if user_id:
                    # If user_id is provided, get user's servers plus global servers (user_id is null)
                    query = query.where(
                        (MCPServer.user_id == user_id) | (MCPServer.user_id.is_(None))
                    )

                servers = await db.scalars(query)
                return [
                    MCPServerModel.model_validate(server) for server in servers.all()
                ]
        except Exception as e:
            print(f"Error getting MCP servers: {e}")
            return []

    async def get_user_created_servers(
        self, user_id: str | None = None
    ) -> list[MCPServerModel]:
        """Get only user-created (external) servers, excluding built-in ones"""
        try:
            async with get_async_db() as db:
                query = select(MCPServer).where(MCPServer.server_type == "user_created")
                if user_id:
                    query = query.where(
                        (MCPServer.user_id == user_id) | (MCPServer.user_id.is_(None))
                    )

                servers = await db.scalars(query)
                return [
                    MCPServerModel.model_validate(server) for server in servers.all()
                ]
        except Exception as e:
            print(f"Error getting user-created MCP servers: {e}")
            return []

    async def update_server_by_id(
        self, id: str, updated: dict
    ) -> MCPServerModel | None:
        try:
            async with get_async_db() as db:
                server = await db.get(MCPServer, id)
                if not server:
                    return None

                # Update fields
                for key, value in updated.items():
                    if hasattr(server, key):
                        setattr(server, key, value)

                server.updated_at = int(time.time())
                await db.commit()
                await db.refresh(server)

                return MCPServerModel.model_validate(server)
        except Exception as e:
            print(f"Error updating MCP server: {e}")
            return None

    async def delete_server_by_id(self, id: str) -> bool:
        try:
            async with get_async_db() as db:
                # Check if server exists and is deletable
                server = await db.get(MCPServer, id)
                if not server:
                    return False
                if not server.is_deletable:
                    return False

                await db.delete(server)
                await db.commit()
                return True
        except Exception as e:
            print(f"Error deleting MCP server: {e}")
            return False

    async def update_server_tools(self, id: str, tools: list) -> MCPServerModel | None:
        """Update the tools list for a server"""
        return await self.update_server_by_id(id, {"tools": tools})

    async def update_server_capabilities(
        self, id: str, capabilities: dict
    ) -> MCPServerModel | None:
        """Update the capabilities for a server"""
        return await self.update_server_by_id(id, {"capabilities": capabilities})

    async def update_server_status(
        self, id: str, is_active: bool
    ) -> MCPServerModel | None:
        """Update the active status of a server"""
        return await self.update_server_by_id(id, {"is_active": is_active})


MCPServers = MCPServerTable()
