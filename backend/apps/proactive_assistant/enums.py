from django.db import models


class SuggestionType(models.TextChoices):
    MEETING_REMINDER = "meeting_reminder", "Meeting reminder"
    DEADLINE_REMINDER = "deadline_reminder", "Deadline reminder"
    REPLY_SUGGESTION = "reply_suggestion", "Reply suggestion"
    FOLLOW_UP_REMINDER = "follow_up_reminder", "Follow-up reminder"
    PAYMENT_REMINDER = "payment_reminder", "Payment reminder"
    TRAVEL_REMINDER = "travel_reminder", "Travel reminder"
    INTERVIEW_REMINDER = "interview_reminder", "Interview reminder"
    GOVERNMENT_DEADLINE = "government_deadline", "Government deadline"
    HOSPITAL_APPOINTMENT = "hospital_appointment", "Hospital appointment"
    VISA_REMINDER = "visa_reminder", "Visa reminder"
    PACKAGE_DELIVERY = "package_delivery", "Package delivery"
    BILL_DUE = "bill_due", "Bill due"
    TASK_EXTRACTION = "task_extraction", "Task extraction"
    CALENDAR_EVENT = "calendar_event", "Calendar event"
    SPAM_WARNING = "spam_warning", "Spam warning"
    PHISHING_WARNING = "phishing_warning", "Phishing warning"


class SuggestedAction(models.TextChoices):
    NONE = "none", "No action"
    REPLY = "reply", "Reply"
    GENERATE_REPLY = "generate_reply", "Generate reply"
    SUMMARIZE = "summarize", "Summarize"
    TRANSLATE = "translate", "Translate"
    ARCHIVE = "archive", "Archive"
    MARK_IMPORTANT = "mark_important", "Mark important"
    CREATE_REMINDER = "create_reminder", "Create reminder"
    ADD_TO_CALENDAR = "add_to_calendar", "Add to calendar"
    CALL_SENDER = "call_sender", "Call sender"
    OPEN_ATTACHMENT = "open_attachment", "Open attachment"
    REVIEW_SECURITY = "review_security", "Review security"


class SuggestionStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SHOWN = "shown", "Shown"
    ACCEPTED = "accepted", "Accepted"
    DISMISSED = "dismissed", "Dismissed"
    COMPLETED = "completed", "Completed"
    EXPIRED = "expired", "Expired"
    SUPPRESSED = "suppressed", "Suppressed"


class DeliveryMethod(models.TextChoices):
    NONE = "none", "Do nothing"
    IN_APP = "in_app", "In-app suggestion"
    PUSH = "push", "Push notification"
    POPUP = "popup", "Popup"
    VOICE = "voice", "Speak"


class HistoryEvent(models.TextChoices):
    CREATED = "created", "Created"
    PRESENTED = "presented", "Presented"
    ACCEPTED = "accepted", "Accepted"
    DISMISSED = "dismissed", "Dismissed"
    COMPLETED = "completed", "Completed"
    EXPIRED = "expired", "Expired"
    SUPPRESSED = "suppressed", "Suppressed"


class FeedbackType(models.TextChoices):
    ACCEPTED = "accepted", "Accepted"
    DISMISSED = "dismissed", "Dismissed"
    HELPFUL = "helpful", "Helpful"
    NOT_HELPFUL = "not_helpful", "Not helpful"
    INCORRECT = "incorrect", "Incorrect"


class BehaviorType(models.TextChoices):
    EMAIL_OPENED = "email_opened", "Email opened"
    EMAIL_ARCHIVED = "email_archived", "Email archived"
    EMAIL_REPLIED = "email_replied", "Email replied"
    EMAIL_IGNORED = "email_ignored", "Email ignored"
    SUGGESTION_ACCEPTED = "suggestion_accepted", "Suggestion accepted"
    SUGGESTION_DISMISSED = "suggestion_dismissed", "Suggestion dismissed"
    VOICE_SUMMARY_REQUESTED = "voice_summary_requested", "Voice summary requested"
    LANGUAGE_SELECTED = "language_selected", "Language selected"
