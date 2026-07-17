from app.agent.schemas import ProcessedEmail


class ConsoleNotifier:
    def send_digest(self, emails: list[ProcessedEmail]) -> None:
        if not emails:
            print("No high-priority emails to notify.")
            return

        print("\nHigh-priority email digest")
        print("=" * 32)
        for processed in emails:
            message = processed.message
            analysis = processed.analysis
            print(f"[P{analysis.priority}] {message.subject}")
            print(f"From: {message.sender}")
            print(f"Summary: {analysis.summary}")
            print(f"Needs reply: {'yes' if analysis.needs_reply else 'no'}")
            if analysis.deadline:
                print(f"Deadline: {analysis.deadline}")
            if analysis.action_items:
                print("Actions: " + "; ".join(analysis.action_items))
            print("-" * 32)
