import asyncio
async def main():
    print("Hello...",end="")
    await asyncio.sleep(1)
    print("World!")

rout = asyncio.run(main())
# rout = main()
print(rout)