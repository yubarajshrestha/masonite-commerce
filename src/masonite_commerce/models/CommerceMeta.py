"""CommerceMeta Model."""
from masoniteorm.models import Model
from masoniteorm.relationships import belongs_to


class CommerceMeta(Model):
    """CommerceMeta Model."""

    __table__ = "commerce_metas"
    __primary_key__ = "id"
    
    __fillable__ = ["product_id", "sku", "virtual", "downloadable", "min_price", "max_price", "on_sale", "stock_quantity", "stock_status", "rating_count", "average_rating", "total_sales", "tax_status"]

    @belongs_to
    def product(self):
        """Returns the product for this meta."""
        from ..models.CommerceProduct import CommerceProduct

        return CommerceProduct