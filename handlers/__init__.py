"""Handlers package — exports all routers in priority order."""

from handlers import (
    start, booking, quiz, portfolio, faq, trust, 
    admin, cancel, confirmation, feedback, subscription, 
    fallback
)

# Order matters: specific handlers first, fallback last
all_routers = [
    start.router,
    subscription.router,
    booking.router,
    cancel.router,
    confirmation.router,
    feedback.router,
    quiz.router,
    portfolio.router,
    faq.router,
    trust.router,
    admin.router,
    fallback.router,  # must be last — catches everything else
]
