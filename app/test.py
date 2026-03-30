from typing import Annotated

from fastapi import Depends, FastAPI

app = FastAPI()


def FixedContentQueryChecker(fixed_content: str, q: str = ""):
    return fixed_content in q


@app.get("/query-checker/")
async def read_query_check(fixed_content_included: Annotated[bool, Depends(FixedContentQueryChecker("bar"))]):
    return {"fixed_content_in_query": fixed_content_included}