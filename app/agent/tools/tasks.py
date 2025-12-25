from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import Task, User

class TaskTool:
    def __init__(self, db: AsyncSession, user: User):
        self.db = db
        self.user = user

    async def list_tasks(self, status: str = None):
        query = select(Task).where(Task.owner_id == self.user.id)
        if status:
            query = query.where(Task.status == status)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def add_task(self, title: str, description: str = None):
        new_task = Task(title=title, description=description, owner_id=self.user.id)
        self.db.add(new_task)
        await self.db.commit()
        await self.db.refresh(new_task)
        return new_task

    async def complete_task(self, task_id: int):
        query = select(Task).where(Task.id == task_id, Task.owner_id == self.user.id)
        result = await self.db.execute(query)
        task = result.scalars().first()
        if task:
            task.status = "completed"
            await self.db.commit()
            return task
        return None
