![Tests](https://github.com/designcomputer/singlestore_mcp_server/actions/workflows/test.yml/badge.svg)
# SingleStore MCP Server

A Model Context Protocol (MCP) server that enables secure interaction with SingleStore databases. This server allows AI assistants to list tables, read data, and execute SQL queries through a controlled interface, making database exploration and analysis safer and more structured.

## Features

- List available SingleStore tables as resources
- Read table contents with support for various data formats (including BSON and JSON)
- Execute SQL queries with proper error handling
- Support for SingleStore-specific data types and functions
- Secure database access through environment variables
- Comprehensive logging

## Installation

```bash
pip install singlestore-mcp-server
```

## Configuration

Set the following environment variables:

```bash
SINGLESTORE_HOST=your_workspace_host
SINGLESTORE_PORT=3306  # Default SingleStore port
SINGLESTORE_USER=your_username
SINGLESTORE_PASSWORD=your_password
SINGLESTORE_DATABASE=your_database
```

## Usage

### With Claude Desktop

Add this to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "singlestore": {
      "command": "uv",
      "args": [
        "--directory", 
        "path/to/singlestore_mcp_server",
        "run",
        "singlestore_mcp_server"
      ],
      "env": {
        "SINGLESTORE_HOST": "your_workspace_host",
        "SINGLESTORE_PORT": "3306",
        "SINGLESTORE_USER": "your_username",
        "SINGLESTORE_PASSWORD": "your_password",
        "SINGLESTORE_DATABASE": "your_database"
      }
    }
  }
}
```

### As a standalone server

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python -m singlestore_mcp_server
```

## Development

```bash
# Clone the repository
git clone https://github.com/yourusername/singlestore_mcp_server.git
cd singlestore_mcp_server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest
```

## SingleStore-Specific Features

- Support for BSON data type and operations
- Native JSON handling with SingleStore JSON functions
- Support for SingleStore Kai (MongoDB API compatibility)
- Proper handling of SingleStore-specific data types

## Security Considerations

- Never commit environment variables or credentials
- Use a database user with minimal required permissions
- Consider implementing query whitelisting for production use
- Monitor and log all database operations

## Security Best Practices

This MCP server requires database access to function. For security:

1. **Create a dedicated SingleStore user** with minimal permissions
2. **Never use admin credentials** or administrative accounts
3. **Restrict database access** to only necessary operations
4. **Enable logging** for audit purposes
5. **Regular security reviews** of database access

See [SingleStore Security Configuration Guide](https://github.com/designcomputer/singlestore_mcp_server/blob/main/SECURITY.md) for detailed instructions on:
- Creating a restricted SingleStore user
- Setting appropriate permissions
- Monitoring database access
- Security best practices

⚠️ IMPORTANT: Always follow the principle of least privilege when configuring database access.

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

