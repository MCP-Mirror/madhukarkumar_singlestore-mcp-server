import os
import logging
from typing import Dict, List, Optional, Any
import singlestoredb as s2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import mcp.server
import mcp.server.models
import mcp.server.stdio
import mcp.types as types

# Configure logging with INFO level to track all database operations
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QueryRequest(BaseModel):
    """
    Pydantic model for SQL query requests.
    
    Attributes:
        query (str): The SQL query to execute
        parameters (Optional[Dict[str, Any]]): Optional parameters for query substitution
    """
    query: str
    parameters: Optional[Dict[str, Any]] = None

class Resource(BaseModel):
    """
    Pydantic model representing a database resource (table).
    
    Attributes:
        id (str): Unique identifier for the resource (table name)
        type (str): Resource type (e.g., "table")
        attributes (Dict[str, Any]): Additional resource metadata
    """
    id: str
    type: str
    attributes: Dict[str, Any]

# Initialize FastAPI application
app = FastAPI()

def get_db_connection():
    """
    Creates and returns a SingleStore database connection.
    
    Environment Variables Required:
        SINGLESTORE_HOST: Database host address
        SINGLESTORE_PORT: Database port (default: 3306)
        SINGLESTORE_USER: Database username
        SINGLESTORE_PASSWORD: Database password
        SINGLESTORE_DATABASE: Target database name
    
    Returns:
        singlestoredb.Connection: Database connection object
    
    Raises:
        HTTPException: If connection fails
    """
    try:
        conn = s2.connect(
            host=os.getenv("SINGLESTORE_HOST"),
            port=int(os.getenv("SINGLESTORE_PORT", "3306")),
            user=os.getenv("SINGLESTORE_USER"),
            password=os.getenv("SINGLESTORE_PASSWORD"),
            database=os.getenv("SINGLESTORE_DATABASE"),
            results_type='dict'  # Return results as dictionaries for easier JSON serialization
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection error: {str(e)}")
        raise HTTPException(status_code=500, detail="Database connection failed")

# Create MCP server instance
server = mcp.server.Server("singlestore-server")

# Add resource capabilities
@server.list_resources()
async def handle_list_resources() -> list[types.Resource]:
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                SELECT 
                    TABLE_NAME,
                    TABLE_TYPE,
                    TABLE_COMMENT,
                    CREATE_TIME
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = DATABASE()
            """)
            tables = cur.fetchall()
            
            resources = []
            for table in tables:
                resource = types.Resource(
                    id=table['TABLE_NAME'],
                    type="table",
                    attributes={
                        "name": table['TABLE_NAME'],
                        "type": table['TABLE_TYPE'],
                        "comment": table['TABLE_COMMENT'],
                        "created_at": table['CREATE_TIME'].isoformat() if table['CREATE_TIME'] else None
                    }
                )
                resources.append(resource)
            return resources
    finally:
        conn.close()

@server.read_resource()
async def handle_read_resource(resource_id: str) -> types.ResourceContent:
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Verify table exists
            cur.execute("""
                SELECT TABLE_NAME 
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = %s
            """, (resource_id,))
            
            if not cur.fetchone():
                raise ValueError("Resource not found")
            
            cur.execute(f"SELECT * FROM {resource_id}")
            rows = cur.fetchall()
            
            return types.ResourceContent(
                type="application/json",
                content=json.dumps({"data": rows})
            )
    finally:
        conn.close()

# Add tool capabilities for custom queries
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="execute_query",
            description="Execute a custom SQL query",
            parameters=[
                types.Parameter(
                    name="query",
                    description="SQL query to execute",
                    required=True
                ),
                types.Parameter(
                    name="parameters",
                    description="Query parameters",
                    required=False
                )
            ]
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.Content]:
    if name != "execute_query":
        raise ValueError(f"Unknown tool: {name}")
        
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            if arguments.get("parameters"):
                cur.execute(arguments["query"], arguments["parameters"])
            else:
                cur.execute(arguments["query"])
            
            if cur.description:
                rows = cur.fetchall()
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"data": rows})
                )]
            else:
                return [types.TextContent(
                    type="text",
                    text=json.dumps({"affected_rows": cur.rowcount})
                )]
    finally:
        conn.close()

# Main entry point
async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            mcp.server.models.InitializationOptions(
                server_name="singlestore",
                server_version="0.1.0",
                capabilities=server.get_capabilities()
            )
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 