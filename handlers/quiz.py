"""Handler: Quiz — 3-step consultation to recommend a service."""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

import database as db
from texts import (
    QUIZ_INTRO, QUIZ_Q1, QUIZ_Q2, QUIZ_Q3,
    QUIZ_FIRST_TIME, QUIZ_EXPERIENCED,
    quiz_recommendation,
)
from keyboards import (
    quiz_services_kb, quiz_experience_kb,
    quiz_priority_kb, quiz_result_kb,
)

router = Router()


class QuizStates(StatesGroup):
    choosing_service = State()
    choosing_experience = State()
    choosing_priority = State()


@router.callback_query(F.data == "quiz_start")
async def quiz_start(callback: CallbackQuery, state: FSMContext) -> None:
    """Start the consultation quiz."""
    await state.clear()
    await callback.answer()
    await db.log_interaction(callback.from_user.id, "quiz_start")

    await callback.message.edit_text(
        f"{QUIZ_INTRO}\n\n<b>{QUIZ_Q1}</b>",
        reply_markup=quiz_services_kb(),
    )
    await state.set_state(QuizStates.choosing_service)


@router.callback_query(F.data.startswith("quiz_svc:"), QuizStates.choosing_service)
async def quiz_step2(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 2 — experience level."""
    service_key = callback.data.split(":")[1]
    await state.update_data(service=service_key)
    await callback.answer()

    await callback.message.edit_text(
        f"<b>{QUIZ_Q2}</b>",
        reply_markup=quiz_experience_kb(),
    )
    await state.set_state(QuizStates.choosing_experience)


@router.callback_query(F.data.startswith("quiz_exp:"), QuizStates.choosing_experience)
async def quiz_step3(callback: CallbackQuery, state: FSMContext) -> None:
    """Step 3 — priority."""
    experience = callback.data.split(":")[1]
    await state.update_data(experience=experience)
    await callback.answer()

    # Show encouragement based on experience
    encouragement = QUIZ_FIRST_TIME if experience == "first" else QUIZ_EXPERIENCED
    await callback.message.edit_text(
        f"{encouragement}\n\n<b>{QUIZ_Q3}</b>",
        reply_markup=quiz_priority_kb(),
    )
    await state.set_state(QuizStates.choosing_priority)


@router.callback_query(F.data.startswith("quiz_pri:"), QuizStates.choosing_priority)
async def quiz_result(callback: CallbackQuery, state: FSMContext) -> None:
    """Show personalized recommendation."""
    priority = callback.data.split(":")[1]
    data = await state.get_data()
    service_key = data.get("service", "manicure")
    await state.clear()
    await callback.answer()

    await db.log_interaction(callback.from_user.id, f"quiz_result_{service_key}")

    recommendation = quiz_recommendation(service_key, priority)
    await callback.message.edit_text(recommendation, reply_markup=quiz_result_kb())
