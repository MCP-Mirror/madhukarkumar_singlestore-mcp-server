import os
import logging
from typing import Dict, List, Optional, Any
import singlestoredb as s2
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

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

@app.get("/resources")
async def list_resources() -> List[Resource]:
    """
    Lists all available tables in the database as MCP resources.
    
    Returns:
        List[Resource]: List of available database tables with their metadata
    
    Example Response:
        [
            {
                "id": "users",
                "type": "table",
                "attributes": {
                    "name": "users",
                    "type": "BASE TABLE",
                    "comment": "User accounts table",
                    "created_at": "2024-03-20T10:00:00"
                }
            }
        ]
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Query to get tables and their details from information schema
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
                resource = Resource(
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
    except Exception as e:
        logger.error(f"Error listing resources: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.get("/resources/{resource_id}")
async def get_resource(resource_id: str) -> Dict[str, Any]:
    """
    Retrieves the contents of a specific table.
    
    Args:
        resource_id (str): The name of the table to query
    
    Returns:
        Dict[str, Any]: Dictionary containing the table's rows
    
    Raises:
        HTTPException: If table doesn't exist or query fails
    
    Example Response:
        {
            "data": [
                {"id": 1, "name": "John Doe", "email": "john@example.com"},
                {"id": 2, "name": "Jane Smith", "email": "jane@example.com"}
            ]
        }
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # First verify the table exists to provide better error messages
            cur.execute("""
                SELECT TABLE_NAME 
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = %s
            """, (resource_id,))
            
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Resource not found")
            
            # Get table contents
            cur.execute(f"SELECT * FROM {resource_id}")
            rows = cur.fetchall()
            
            # Handle special SingleStore data types
            for row in rows:
                for key, value in row.items():
                    if isinstance(value, (bytes, bytearray)):
                        # Convert binary data (BSON, BLOB) to string representation
                        row[key] = f"<binary data length={len(value)}>"
            
            return {"data": rows}
    except Exception as e:
        logger.error(f"Error getting resource {resource_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post("/query")
async def execute_query(request: QueryRequest) -> Dict[str, Any]:
    """
    Executes a custom SQL query with optional parameters.
    
    Args:
        request (QueryRequest): Object containing the query and optional parameters
    
    Returns:
        Dict[str, Any]: Query results or affected rows count
    
    Raises:
        HTTPException: If query execution fails
    
    Example Request:
        {
            "query": "SELECT * FROM users WHERE age > %s",
            "parameters": {"age": 21}
        }
    
    Example Response (SELECT):
        {
            "data": [
                {"id": 1, "name": "John", "age": 25},
                {"id": 2, "name": "Jane", "age": 23}
            ]
        }
    
    Example Response (INSERT/UPDATE/DELETE):
        {
            "affected_rows": 1
        }
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            # Execute the query with parameters if provided
            if request.parameters:
                cur.execute(request.query, request.parameters)
            else:
                cur.execute(request.query)
            
            # Return results for SELECT queries
            if cur.description:
                rows = cur.fetchall()
                return {"data": rows}
            else:
                # Return affected rows count for INSERT/UPDATE/DELETE
                return {"affected_rows": cur.rowcount}
    except Exception as e:
        logger.error(f"Query execution error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 