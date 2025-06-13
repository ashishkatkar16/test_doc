#!/usr/bin/env python3
"""
MCP Server for Document Processing System

This server exposes the document processing functionality through MCP tools,
allowing AI assistants to upload documents, check processing status, approve documents,
and retrieve results.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
import os
import shutil
import base64

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import (
    Resource, Tool, TextContent, ImageContent, EmbeddedResource,
    CallToolRequest, CallToolResult, ListResourcesRequest, ListResourcesResult,
    ListToolsRequest, ListToolsResult, ReadResourceRequest, ReadResourceResult
)

# Import your existing modules
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.config import settings
from app.database import get_db, create_tables, SessionLocal
from app.models import Document, ProcessingResult
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-document-processor")

# Initialize the MCP server
server = Server("document-processor")

# Initialize database on startup
try:
    create_tables()
    logger.info("✅ Database tables created successfully")
except Exception as e:
    logger.error(f"❌ Error creating database tables: {e}")


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    """List available tools for document processing."""
    return [
        Tool(
            name="upload_document",
            description="Upload a document for processing. Supports PDF and EML files.",
            inputSchema={
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name of the file to upload"
                    },
                    "content": {
                        "type": "string",
                        "description": "Base64 encoded file content"
                    }
                },
                "required": ["filename", "content"]
            }
        ),
        Tool(
            name="list_documents",
            description="List all documents in the system with their processing status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter by status (optional): processing, auto_approved, manual_review, quick_review, error",
                        "enum": ["processing", "auto_approved", "manual_review", "quick_review", "error",
                                 "manually_approved"]
                    }
                }
            }
        ),
        Tool(
            name="get_document_details",
            description="Get detailed information about a specific document.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "integer",
                        "description": "ID of the document to retrieve"
                    }
                },
                "required": ["document_id"]
            }
        ),
        Tool(
            name="get_processing_results",
            description="Get processing results for a specific document.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "integer",
                        "description": "ID of the document to get results for"
                    }
                },
                "required": ["document_id"]
            }
        ),
        Tool(
            name="approve_document",
            description="Manually approve a document that requires review.",
            inputSchema={
                "type": "object",
                "properties": {
                    "document_id": {
                        "type": "integer",
                        "description": "ID of the document to approve"
                    }
                },
                "required": ["document_id"]
            }
        ),
        Tool(
            name="get_system_status",
            description="Get system status including database connection and folder information.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls for document processing operations."""

    if name == "upload_document":
        return await upload_document_tool(arguments)
    elif name == "list_documents":
        return await list_documents_tool(arguments)
    elif name == "get_document_details":
        return await get_document_details_tool(arguments)
    elif name == "get_processing_results":
        return await get_processing_results_tool(arguments)
    elif name == "approve_document":
        return await approve_document_tool(arguments)
    elif name == "get_system_status":
        return await get_system_status_tool()
    else:
        raise ValueError(f"Unknown tool: {name}")


async def upload_document_tool(arguments: dict) -> list[TextContent]:
    """Handle document upload."""
    try:
        filename = arguments["filename"]
        content_b64 = arguments["content"]

        # Validate file type
        if not (filename.lower().endswith('.pdf') or filename.lower().endswith('.eml')):
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": "Unsupported file type. Only PDF and EML files are supported.",
                    "supported_types": [".pdf", ".eml"]
                }, indent=2)
            )]

        # Decode base64 content
        try:
            file_content = base64.b64decode(content_b64)
        except Exception as e:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "error": f"Invalid base64 content: {str(e)}"
                }, indent=2)
            )]

        # Create destination directory
        dest_dir = settings.robot_folder_path
        os.makedirs(dest_dir, exist_ok=True)

        # Save file
        file_path = os.path.join(dest_dir, filename)
        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info(f"File uploaded via MCP: {filename}")

        return [TextContent(
            type="text",
            text=json.dumps({
                "message": f"File {filename} uploaded successfully",
                "file_path": file_path,
                "status": "uploaded",
                "note": "Processing will begin automatically via file watcher"
            }, indent=2)
        )]

    except Exception as e:
        logger.error(f"Error uploading file via MCP: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": f"Error uploading file: {str(e)}"
            }, indent=2)
        )]


async def list_documents_tool(arguments: dict) -> list[TextContent]:
    """Handle listing documents."""
    try:
        db = SessionLocal()
        try:
            query = db.query(Document)

            # Apply status filter if provided
            status_filter = arguments.get("status")
            if status_filter:
                query = query.filter(Document.status == status_filter)

            docs = query.all()

            documents = [
                {
                    "id": d.id,
                    "filename": d.filename,
                    "file_path": d.file_path,
                    "status": d.status,
                    "created_at": d.created_at.isoformat() if hasattr(d, 'created_at') and d.created_at else None,
                    "processed_at": d.processed_at.isoformat() if d.processed_at else None,
                }
                for d in docs
            ]

            return [TextContent(
                type="text",
                text=json.dumps({
                    "documents": documents,
                    "total_count": len(documents),
                    "filter_applied": status_filter
                }, indent=2)
            )]

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error listing documents via MCP: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": f"Error fetching documents: {str(e)}"
            }, indent=2)
        )]


async def get_document_details_tool(arguments: dict) -> list[TextContent]:
    """Handle getting document details."""
    try:
        document_id = arguments["document_id"]
        db = SessionLocal()

        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": "Document not found",
                        "document_id": document_id
                    }, indent=2)
                )]

            document_details = {
                "id": doc.id,
                "filename": doc.filename,
                "file_path": doc.file_path,
                "status": doc.status,
                "created_at": doc.created_at.isoformat() if hasattr(doc, 'created_at') and doc.created_at else None,
                "processed_at": doc.processed_at.isoformat() if doc.processed_at else None,
            }

            return [TextContent(
                type="text",
                text=json.dumps({
                    "document": document_details
                }, indent=2)
            )]

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error getting document details via MCP: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": f"Error fetching document: {str(e)}"
            }, indent=2)
        )]


async def get_processing_results_tool(arguments: dict) -> list[TextContent]:
    """Handle getting processing results."""
    try:
        document_id = arguments["document_id"]
        db = SessionLocal()

        try:
            result = (
                db.query(ProcessingResult)
                .filter(ProcessingResult.document_id == document_id)
                .first()
            )

            if not result:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": "Processing results not found",
                        "document_id": document_id,
                        "note": "Document may not have been processed yet"
                    }, indent=2)
                )]

            results = {
                "id": result.id,
                "document_id": result.document_id,
                "overall_score": result.overall_score,
                "requires_manual_review": result.requires_manual_review,
                "created_at": result.created_at.isoformat() if result.created_at else None,
            }

            return [TextContent(
                type="text",
                text=json.dumps({
                    "results": results
                }, indent=2)
            )]

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error getting processing results via MCP: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": f"Error fetching results: {str(e)}"
            }, indent=2)
        )]


async def approve_document_tool(arguments: dict) -> list[TextContent]:
    """Handle manual document approval."""
    try:
        document_id = arguments["document_id"]
        db = SessionLocal()

        try:
            doc = db.query(Document).filter(Document.id == document_id).first()
            if not doc:
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": "Document not found",
                        "document_id": document_id
                    }, indent=2)
                )]

            # Update document status
            doc.status = "manually_approved"
            db.commit()

            # Try to queue email prep if Celery is available
            email_queued = False
            try:
                from workers.tasks import celery_app
                celery_app.send_task("workers.tasks.prepare_email", args=[document_id])
                email_queued = True
                logger.info(f"Queued email preparation for document {document_id} via MCP")
            except ImportError:
                logger.warning("Celery not installed, skipped email queue")
            except Exception as e:
                logger.error(f"Error queuing email via MCP: {e}")

            return [TextContent(
                type="text",
                text=json.dumps({
                    "message": "Document approved manually",
                    "document_id": document_id,
                    "new_status": "manually_approved",
                    "email_queued": email_queued
                }, indent=2)
            )]

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error approving document via MCP: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": f"Error approving document: {str(e)}"
            }, indent=2)
        )]


async def get_system_status_tool() -> list[TextContent]:
    """Handle getting system status."""
    try:
        db = SessionLocal()

        try:
            # Get database statistics
            document_count = db.query(Document).count()
            result_count = db.query(ProcessingResult).count()

            # Get watch folder contents
            watch_folder_contents = []
            try:
                if os.path.exists(settings.robot_folder_path):
                    watch_folder_contents = os.listdir(settings.robot_folder_path)
            except Exception as e:
                watch_folder_contents = [f"Error reading folder: {str(e)}"]

            # Get status breakdown
            status_counts = {}
            try:
                from sqlalchemy import func
                status_results = db.query(
                    Document.status,
                    func.count(Document.id)
                ).group_by(Document.status).all()

                status_counts = {status: count for status, count in status_results}
            except Exception as e:
                status_counts = {"error": f"Could not get status breakdown: {str(e)}"}

            system_status = {
                "database": {
                    "connected": True,
                    "document_count": document_count,
                    "result_count": result_count,
                    "status_breakdown": status_counts
                },
                "filesystem": {
                    "watch_folder": settings.robot_folder_path,
                    "watch_folder_exists": os.path.exists(settings.robot_folder_path),
                    "watch_folder_contents": watch_folder_contents
                },
                "server_info": {
                    "mcp_server": "document-processor",
                    "version": "1.0.0"
                }
            }

            return [TextContent(
                type="text",
                text=json.dumps(system_status, indent=2)
            )]

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error getting system status via MCP: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": f"Error getting system status: {str(e)}",
                "database": {"connected": False}
            }, indent=2)
        )]


async def main():
    """Main entry point for the MCP server."""
    # Import stdio functions from mcp.server with explicit error handling
    try:
        from mcp.server.stdio import stdio_server
    except ImportError as e:
        logger.error(f"Failed to import MCP stdio server: {e}")
        logger.error("Make sure you have the MCP library installed: pip install mcp")
        return

    logger.info("Starting Document Processing MCP Server...")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="document-processor",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())