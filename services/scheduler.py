import logging
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from telegram.ext import ContextTypes
from services.database import AsyncSessionLocal, Appointment, Service, User

logger = logging.getLogger(__name__)

async def send_appointment_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Job handler for scheduled appointment reminders."""
    job_data = context.job.data
    appointment_id = job_data.get("appointment_id")
    user_id = job_data.get("user_id")

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Appointment, Service)
            .join(Service, Appointment.service_id == Service.id)
            .where(Appointment.id == appointment_id, Appointment.status == "Confirmed")
        )
        data = result.first()
        if not data:
            logger.info("Reminder skipped: Appointment %s not found or no longer confirmed.", appointment_id)
            return

        appointment, service = data
        formatted_time = appointment.start_time.strftime("%Y-%m-%d %H:%M UTC")

        text = (
            f"⏰ **Upcoming Appointment Reminder!**\n\n"
            f"🔹 **Service:** {service.name}\n"
            f"📅 **Date & Time:** {formatted_time}\n"
            f"⌛ **Duration:** {service.duration_minutes} minutes\n\n"
            f"We look forward to serving you! Use /appointments if you need to reschedule."
        )

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=text,
                parse_mode="Markdown"
            )
            logger.info("Sent reminder for appointment %s to user %s", appointment_id, user_id)
        except Exception as e:
            logger.error("Failed to send reminder for appointment %s to user %s: %s", appointment_id, user_id, e)

async def auto_complete_past_appointments(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodic job to automatically set past confirmed appointments to 'Completed'."""
    async with AsyncSessionLocal() as session:
        try:
            now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
            stmt = (
                update(Appointment)
                .where(
                    Appointment.end_time < now_utc,
                    Appointment.status == "Confirmed"
                )
                .values(status="Completed")
            )
            result = await session.execute(stmt)
            await session.commit()
            if result.rowcount > 0:
                logger.info("Auto-completed %s past appointments.", result.rowcount)
        except Exception as e:
            await session.rollback()
            logger.error("Error running auto_complete_past_appointments job: %s", e)

def schedule_appointment_reminder(job_queue, appointment_id: int, user_id: int, start_time: datetime, reminder_minutes: int) -> None:
    """Calculates trigger time and schedules a reminder job in JobQueue."""
    if reminder_minutes <= 0:
        return

    reminder_time = start_time - timedelta(minutes=reminder_minutes)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # Don't schedule if the reminder time has already passed
    if reminder_time <= now:
        logger.warning("Reminder time %s is in the past for appointment %s. Skipping.", reminder_time, appointment_id)
        return

    job_name = f"reminder_{appointment_id}"
    
    # Remove any existing job for this appointment
    existing_jobs = job_queue.get_jobs_by_name(job_name)
    for job in existing_jobs:
        job.schedule_removal()

    job_queue.run_once(
        send_appointment_reminder,
        when=reminder_time,
        data={"appointment_id": appointment_id, "user_id": user_id},
        name=job_name
    )
    logger.info("Scheduled reminder for appointment %s at %s", appointment_id, reminder_time)
