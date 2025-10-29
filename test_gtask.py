"""Main module for demonstrating the task client."""

import contextlib
import logging

import gtask_client_impl  # noqa: F401
import task_client_api

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:  # noqa: PLR0915, PLR0912, C901 # Just a test script
    """Initialize the client and demonstrate all task client methods."""
    # Now, get_client() returns a GTaskClient instance...
    client = task_client_api.get_client(interactive=False)

    # Test 1: List all tasklists
    logger.info("Test 1: Listing all tasklists...")
    tasklists = client.list_tasklists()
    logger.info("Found %d tasklist(s)", len(tasklists))

    if not tasklists:
        logger.info("No tasklists found. Creating a test tasklist...")
        # For insert, we'd need a TaskList object, but we can't create one without raw_data
        # So we'll skip this test if no tasklists exist
        logger.info("Skipping further tests - no tasklists available.")
        return

    # Display tasklists
    for i, tasklist in enumerate(tasklists, 1):
        logger.info("TaskList %d: %s (ID: %s)", i, tasklist.title, tasklist.id)

    # Test 2: Get tasks from the first tasklist
    test_tasklist = tasklists[0]
    logger.info("\nTest 2: Listing tasks from tasklist '%s'...", test_tasklist.title)
    tasks = client.list_tasks(test_tasklist)

    logger.info("Found %d task(s) in tasklist '%s'", len(tasks), test_tasklist.title)

    # Display tasks
    for i, task in enumerate(tasks, 1):
        status_emoji = "✓" if task.status == "completed" else "○"
        logger.info(
            "Task %d: %s %s (ID: %s)",
            i,
            status_emoji,
            task.title,
            task.id,
        )
        if task.notes:
            logger.info("  Notes: %s", task.notes[:50])
        if task.due:
            logger.info("  Due: %s", task.due)

    # Test 3: Get a specific task by ID
    if tasks:
        test_task_id = tasks[0].id
        logger.info("\nTest 3: Getting task by ID: %s...", test_task_id)
        with contextlib.suppress(Exception):
            task = client.get_task(test_task_id)
            logger.info("Retrieved task: %s (Status: %s)", task.title, task.status)

    # Test 4: Create a new task (if we have a tasklist)
    if test_tasklist and len(tasks) >= 0:  # Allow creating even if no tasks exist
        logger.info("\nTest 4: Creating a new test task...")
        # We need to create a Task object, but we can't easily do that without raw_data
        # For now, we'll note that this requires a Task object with at least a title
        logger.info("Note: insert_task requires a Task object. Skipping creation test.")

    # Test 5: Delete a tasklist (WARNING: This is destructive!)
    # Only test if we have more than one tasklist to avoid deleting all tasklists
    if len(tasklists) > 1:
        logger.info("\nTest 5: Deleting a tasklist (destructive operation)...")
        delete_tasklist = tasklists[-1]  # Delete the last tasklist
        try:
            confirmation = input(f"Type 'DELETE' to confirm deletion of tasklist '{delete_tasklist.title}': ")
            if confirmation == "DELETE":
                success = client.delete_tasklist(delete_tasklist)
                if success:
                    logger.info(
                        "Tasklist '%s' (ID: %s) deleted successfully.",
                        delete_tasklist.title,
                        delete_tasklist.id,
                    )
                else:
                    logger.info(
                        "Failed to delete tasklist '%s' (ID: %s).",
                        delete_tasklist.title,
                        delete_tasklist.id,
                    )
        except EOFError:
            # This means that CircleCI or another non-interactive environment is
            # not going to actually delete anything
            logger.info("Non-interactive environment detected. Skipping deletion.")
    else:
        logger.info(
            "\nTest 5: Skipping tasklist deletion (only %d tasklist(s) found)",
            len(tasklists),
        )

    # Test 6: Delete a task (WARNING: This is destructive!)
    # Only test if we have tasks in the first tasklist
    if tasks and len(tasks) > 0:
        logger.info("\nTest 6: Deleting a task (destructive operation)...")
        delete_task = tasks[-1]  # Delete the last task
        try:
            confirmation = input(f"Type 'DELETE' to confirm deletion of task '{delete_task.title}': ")
            if confirmation == "DELETE":
                success = client.delete_task(delete_task.id)
                if success:
                    logger.info(
                        "Task '%s' (ID: %s) deleted successfully.",
                        delete_task.title,
                        delete_task.id,
                    )
                else:
                    logger.info(
                        "Failed to delete task '%s' (ID: %s).",
                        delete_task.title,
                        delete_task.id,
                    )
        except EOFError:
            # This means that CircleCI or another non-interactive environment is
            # not going to actually delete anything
            logger.info("Non-interactive environment detected. Skipping deletion.")
    else:
        logger.info("\nTest 6: Skipping task deletion (no tasks found)")

    logger.info("\nDemo complete.")


if __name__ == "__main__":
    main()
