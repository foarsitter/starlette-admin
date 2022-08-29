from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Union

from starlette.requests import Request
from starlette_admin import IntegerField, StringField, TagsField, TextAreaField
from starlette_admin.exceptions import FormValidationError
from starlette_admin.views import BaseModelView


@dataclass
class Post:
    id: int
    title: str
    content: str
    tags: List[str]

    def is_valid_for_term(self, term):
        return (
            str(term).lower() in self.title.lower()
            or str(term).lower() in self.content.lower()
            or any([str(term).lower() in tag.lower() for tag in self.tags])
        )

    def update(self, data: Dict):
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)


db: Dict[int, Post] = dict()
next_id = 1


def filter_values(values: Iterable[Post], term):
    filtered_values = []
    for value in values:
        if value.is_valid_for_term(term):
            filtered_values.append(value)
    return filtered_values


class PostView(BaseModelView):
    identity = "post"
    name = "Post"
    label = "Blog Posts"
    icon = "fa fa-blog"
    pk_attr = "id"
    fields = (
        IntegerField("id"),
        StringField("title"),
        TextAreaField("content"),
        TagsField("tags"),
    )
    sortable_fields = ("id", "title", "content")
    search_builder = False

    async def count(
        self,
        request: Request,
        where: Union[Dict[str, Any], str, None] = None,
    ) -> int:
        values = list(db.values())
        if where is not None:
            values = filter_values(values, where)
        return len(values)

    async def find_all(
        self,
        request: Request,
        skip: int = 0,
        limit: int = 100,
        where: Union[Dict[str, Any], str, None] = None,
        order_by: Optional[List[str]] = None,
    ) -> List[Any]:
        values = list(db.values())
        if order_by is not None:
            assert len(order_by) < 2, "Not supported"
            if len(order_by) == 1:
                key, dir = order_by[0].split(maxsplit=1)
                values.sort(key=lambda v: getattr(v, key), reverse=(dir == "desc"))

        if where is not None and isinstance(where, (str, int)):
            values = filter_values(values, where)
        if limit > 0:
            return values[skip : skip + limit]
        return values[skip:]

    async def find_by_pk(self, request: Request, pk):
        return db.get(int(pk), None)

    async def find_by_pks(self, request: Request, pks):
        return [db.get(int(pk)) for pk in pks]

    async def validate_data(self, data: Dict):
        errors = {}
        if data["title"] is None or len(data["title"]) < 3:
            errors["title"] = "Ensure title has at least 03 characters"
        if data["tags"] is None or len(data["tags"]) < 1:
            errors["tags"] = "You need at least one tag"
        if len(errors) > 0:
            raise FormValidationError(errors)

    async def create(self, request: Request, data: Dict):
        await self.validate_data(data)
        global next_id
        obj = Post(id=next_id, **data)
        db[next_id] = obj
        next_id += 1
        return obj

    async def edit(self, request: Request, pk, data: Dict):
        await self.validate_data(data)
        db[int(pk)].update(data)
        return db[int(pk)]

    async def delete(self, request: Request, pks: List[Any]) -> Optional[int]:
        cnt = 0
        for pk in pks:
            value = await self.find_by_pk(request, pk)
            if value is not None:
                del db[int(pk)]
                cnt += 1
        return cnt
