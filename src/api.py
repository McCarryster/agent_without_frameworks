"""
Main API module for the property management system.
Provides email processing and query handling functionality.
"""

import argparse
import logging
from backend.inbox_manager import InboxManager, EmailMessage
import app
import app.dependencies
from app.agents import EmailAgent, get_email_agent, get_query_agent, BaseAgent, EmailAgent, QueryAgent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_email(subject: str, body: str, sender: str) -> str:
    """
    Process incoming emails to handle property-related requests.
    If response to this email cannot be given with the tools available,
    return <NEEDS MANUAL RESPONSE>.

    Args:
        subject: Email subject line
        body: Email body content
        sender: Email address of the sender

    Returns:
        Response message
    """
    inbox_manager: InboxManager = app.dependencies.get_inbox_manager()
    msg: EmailMessage = inbox_manager.receive_email(
        sender = sender,
        subject=subject,
        body=body
    )
    agent: EmailAgent = get_email_agent()
    success, response = agent.run(
        sender=msg.contact_email,
        topic=msg.subject,
        body=msg.body
    )
    if success:
        print("Email processed successfully.")
        return response
    else:
        print("Email processing failed or requires manual intervention.")
    return "<NEEDS MANUAL RESPONSE>"


def process_query(query: str) -> str:
    """
    Process natural language queries about inbox, listings and calendar.
    If response to this question cannot be given with the tools available,
    return <NEEDS MANUAL RESPONSE>.

    Args:
        query: Natural language query string

    Returns:
        Response to the query
    """
    agent : QueryAgent = get_query_agent()
    success, response = agent.run(query=query)
    if success:
        print("Query processed successfully.")
        return response
    else:
        print("Query processing failed or requires manual intervention.")
    return "<NEEDS MANUAL RESPONSE>"


def main():
    """CLI interface for testing API methods."""
    parser = argparse.ArgumentParser(
        description="Property Management System API"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--query",
        type=str,
        help="Process a natural language query"
    )
    group.add_argument(
        "--email",
        nargs=3,
        metavar=("SENDER", "SUBJECT", "BODY"),
        help="Process an email (requires sender, subject, and body)"
    )

    args = parser.parse_args()

    if args.query:
        logger.info(f"Processing query: {args.query}")
        result = process_query(args.query)
        print(f"Result: {result}")
    elif args.email:
        sender, subject, body = args.email
        logger.info(f"Processing email from: {sender}")
        result = process_email(subject, body, sender)
        print(f"Result: {result}")


if __name__ == "__main__":
    main()
