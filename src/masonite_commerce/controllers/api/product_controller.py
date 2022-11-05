# flake8: noqa F401
from masonite.controllers import Controller
from masonite.request import Request
from masonite.response import Response

from src.masonite_commerce.models.CommerceComment import CommerceComment
from src.masonite_commerce.models.CommerceProduct import CommerceProduct
from src.masonite_commerce.models.CommerceCategory import CommerceCategory
from src.masonite_commerce.models.CommerceTag import CommerceTag
from src.masonite_commerce.models.CommerceProductMeta import CommerceProductMeta
from masoniteorm.query import QueryBuilder
from masoniteorm.expressions import JoinClause
from src.masonite_commerce.validators.product_rule import ProductRule
from src.masonite_commerce.constants.http_status_codes import (
    STATUS_CREATED,
    STATUS_NOT_FOUND,
    STATUS_UNPROCESSABLE,
)


class ProductController(Controller):
    def __init__(self, response: Response, request: Request) -> None:
        self.response = response
        self.request = request

    def index(self):
        """Returns a list of products"""

        per_page = int(self.request.input("per-page", 10))
        page = int(self.request.input("page", 1))

        comment_query = JoinClause("commerce_comments as comments", clause="left").on(
            "comments.product_id", "=", "commerce_products.id"
        )
        meta_query = JoinClause("commerce_metas as metas", clause="left").on(
            "metas.product_id", "=", "commerce_products.id"
        )

        products = (
            CommerceProduct.select_raw(
                """
                commerce_products.*,
                cast(coalesce(metas.price, 0) as int) as price,
                cast(coalesce(metas.average_rating, 0) as int) as avg_rating,
                metas.stock_status,
                cast(coalesce(metas.stock_quantity, 0) as int) as quantity,
                count(comments.id) as total_comments
            """
            )
            .join(comment_query)
            .join(meta_query)
            .where("commerce_products.status", "=", "published")
            .where("metas.stock_status", "=", "instock")
            .group_by("metas.id, commerce_products.id")
            .paginate(per_page, page)
        )

        return products

    def store(self):
        errors = self.request.validate(ProductRule)

        if errors:
            return self.response.json(
                {"message": "Data validation failed", "errors": errors.all()},
                status=STATUS_UNPROCESSABLE,
            )

        try:
            product_data = self.request.only("title", "slug", "comment_status", "status")
            category_data = self.request.input("categories", [])
            tag_data = self.request.input("tags", [])
            meta_data = self.request.only(
                "sku",
                "virtual",
                "downloadable",
                "price",
                "min_price",
                "max_price",
                "on_sale",
                "stock_quantity",
                "stock_status",
                "tax_status",
            )
            attribute_data = self.request.input("attributes")

            if type(category_data) is not list:
                category_data = [category_data]

            if type(tag_data) is not list:
                tag_data = [tag_data]

            if type(attribute_data) is not list:
                attribute_data = [attribute_data]

            product_data.update({"creator_id": 1})

            product = CommerceProduct.create(product_data)

            categories = CommerceCategory.where_in("id", category_data).get()
            product.save_many("categories", categories)

            tags = CommerceTag.where_in("id", tag_data).get()
            product.save_many("tags", tags)

            meta_data.update({"product_id": product.id})

            meta = CommerceProductMeta.create(meta_data)
            product.attach("meta", meta)

            for attribute in attribute_data:
                attribute.update({"product_id": product.id})

            if len(attribute_data) > 0:
                QueryBuilder().table("commerce_product_attribute").bulk_create(attribute_data)

            return self.response.json(
                {
                    "message": "Product added successfully",
                },
                status=STATUS_CREATED,
            )
        except Exception as e:
            print(e)
            return self.response.json(
                {"message": "Data validation failed", "errors": errors.all()},
                status=STATUS_UNPROCESSABLE,
            )

    def update(self, id: int):
        errors = self.request.validate(ProductRule)

        if errors:
            return self.response.json(
                {"message": "Data validation failed", "errors": errors.all()},
                status=STATUS_UNPROCESSABLE,
            )

        try:
            product = CommerceProduct.find(id)

            if not product:
                return self.response.json(
                    {"message": "Product not found", "errors": errors.all()},
                    status=STATUS_NOT_FOUND,
                )

            product_data = self.request.only("title", "slug", "comment_status", "status")
            category_data = self.request.input("categories", [])
            tag_data = self.request.input("tags", [])
            meta_data = self.request.only(
                "sku",
                "virtual",
                "downloadable",
                "price",
                "min_price",
                "max_price",
                "on_sale",
                "stock_quantity",
                "stock_status",
                "tax_status",
            )
            attribute_data = self.request.input("attributes")

            product.update(product_data)

            if type(category_data) is not list:
                category_data = [category_data]

            if type(tag_data) is not list:
                tag_data = [tag_data]

            if type(attribute_data) is not list:
                attribute_data = [attribute_data]

            categories = CommerceCategory.where_in("id", category_data).get()
            product.detach_many("categories", categories)
            product.save_many("categories", categories)

            tags = CommerceTag.where_in("id", tag_data).get()
            product.detach_many("tags", tags)
            product.save_many("tags", tags)

            meta = CommerceProductMeta.where("product_id", "=", id)
            if not meta:
                meta = CommerceProductMeta.create(meta_data)
                product.attach("meta", meta)
            else:
                meta.update(meta_data)

            for attribute in attribute_data:
                attribute.update({"product_id": product.id})

            attribute_builder = QueryBuilder().table("commerce_product_attribute")

            attribute_builder.where({"product_id": product.id}).delete()

            if len(attribute_data) > 0:
                attribute_builder.bulk_create(attribute_data)

            return self.response.json(
                {
                    "message": "Product updated successfully",
                },
                status=STATUS_CREATED,
            )
        except Exception as e:
            return self.response.json(
                {
                    "message": "Data validation failed",
                    "error": e.message,
                },
                status=STATUS_UNPROCESSABLE,
            )

    def show(self, id: int):
        """Returns a single product"""

        comment_query = JoinClause("commerce_comments as comments", clause="left").on(
            "comments.product_id", "=", "commerce_products.id"
        )
        meta_query = JoinClause("commerce_metas as metas", clause="left").on(
            "metas.product_id", "=", "commerce_products.id"
        )

        product = (
            CommerceProduct.select_raw(
                """
                commerce_products.*,
                cast(coalesce(metas.price, 0) as int) as price,
                cast(coalesce(metas.average_rating, 0) as int) as avg_rating,
                metas.stock_status,
                cast(coalesce(metas.stock_quantity, 0) as int) as quantity,
                count(comments.id) as total_comments
            """
            )
            .join(comment_query)
            .join(meta_query)
            .where("commerce_products.id", "=", id)
            .with_("meta", "categories", "attributes", "tags")
            .group_by("comments.product_id, metas.id, commerce_products.id")
            .first()
        )

        return {
            "data": product.serialize(),
        }

    def comments(self, id: int):
        """Returns a list of comments for a product"""

        per_page = int(self.request.input("per-page", 10))
        page = int(self.request.input("page", 1))

        comments = CommerceComment.where("product_id", "=", id).paginate(per_page, page)

        return comments
