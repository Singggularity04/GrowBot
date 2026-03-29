"""Handlers package — exports all routers in priority order."""

from handlers import start, booking, quiz, portfolio, faq, trust, admin, fallback

# Order matters: specific handlers first, fallback last
all_routers = [
    start.router,
    booking.router,
    quiz.router,
    portfolio.router,
    faq.router,
    trust.router,
    admin.router,
    fallback.router,  # must be last — catches everything else
]
