import asyncio
from typesafe_sdk import AsyncTypeSafeClient, Noul

async def main():
    async with AsyncTypeSafeClient(model="jev-latest") as c:
        r = await c.system_one(
            state={"claim": "All 5 paid orders are now shipped.", "database_check": "Orders still in status paid after this step: 3."},
            questions={"done": Noul(instructions="Does `database_check` show that the work described in `claim` was actually completed?")},
        )
        print(r.nouls["done"].noul, r.model, r.usage)

asyncio.run(main())
