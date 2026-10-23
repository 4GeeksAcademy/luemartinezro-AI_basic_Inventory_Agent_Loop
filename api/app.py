"""
Inventory Management API — FastAPI
===================================
REST API that manages inventory data stored in a CSV file.
Exposes endpoints for listing, adding, updating products and
retrieving low-stock alerts.
"""

import csv
import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CSV_FILE = os.path.join(os.path.dirname(__file__), "..", "products.csv")
LOW_STOCK_THRESHOLD: int = 10  # default threshold (units)

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class ProductCreate(BaseModel):
    """Payload for creating a new product."""

    name: str = Field(..., min_length=1, description="Product name")
    quantity: float = Field(..., ge=0, description="Current stock quantity")
    unit: str = Field(..., min_length=1, description="Unit of measure (e.g. units, kg, liters)")


class ProductUpdate(BaseModel):
    """Payload for updating stock (delta can be positive or negative)."""

    delta: float = Field(
        ...,
        description="Stock change: positive for incoming stock, negative for outgoing",
    )


class Product(ProductCreate):
    """Full product model (includes auto-generated id)."""

    id: int = Field(..., description="Unique product identifier")


# ---------------------------------------------------------------------------
# CSV helpers
# ---------------------------------------------------------------------------

APP = FastAPI(
    title="Coffee Shop Inventory API",
    description="Manage inventory for a small coffee shop supply store.",
    version="1.0.0",
)


def _csv_columns() -> List[str]:
    return ["id", "name", "quantity", "unit"]


def _load_products() -> List[dict]:
    """Load all products from the CSV file. Returns an empty list if the file
    does not exist."""
    if not os.path.isfile(CSV_FILE):
        return []
    with open(CSV_FILE, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        return [row for row in reader]


def _save_products(products: List[dict]) -> None:
    """Overwrite the CSV file with the full list of products."""
    with open(CSV_FILE, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=_csv_columns())
        writer.writeheader()
        writer.writerows(products)


def _next_id(products: List[dict]) -> int:
    """Return the next available product id."""
    if not products:
        return 1
    return max(int(p["id"]) for p in products) + 1


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@APP.get("/inventory", response_model=List[Product])
def list_products():
    """Return the full product list."""
    products = _load_products()
    # Convert id to int for the response model
    return [
        {"id": int(p["id"]), "name": p["name"], "quantity": float(p["quantity"]), "unit": p["unit"]}
        for p in products
    ]


@APP.post("/inventory", response_model=Product, status_code=201)
def add_product(payload: ProductCreate):
    """Add a new product to the inventory."""
    products = _load_products()
    new_id = _next_id(products)
    new_product = {
        "id": new_id,
        "name": payload.name,
        "quantity": payload.quantity,
        "unit": payload.unit,
    }
    products.append(new_product)
    _save_products(products)
    return {"id": new_id, "name": payload.name, "quantity": payload.quantity, "unit": payload.unit}


@APP.patch("/inventory/{product_id}", response_model=Product)
def update_stock(product_id: int, payload: ProductUpdate):
    """Update the stock of an existing product (delta can be positive or
    negative)."""
    products = _load_products()
    for product in products:
        if int(product["id"]) == product_id:
            current_qty = float(product["quantity"])
            new_qty = current_qty + payload.delta
            if new_qty < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock: current quantity is {current_qty}, "
                    f"cannot reduce by {abs(payload.delta)}",
                )
            product["quantity"] = str(new_qty)
            _save_products(products)
            return {
                "id": product_id,
                "name": product["name"],
                "quantity": new_qty,
                "unit": product["unit"],
            }
    raise HTTPException(status_code=404, detail=f"Product with id {product_id} not found")


@APP.get("/inventory/alerts", response_model=List[Product])
def low_stock_alerts(threshold: int = Query(LOW_STOCK_THRESHOLD, ge=0)):
    """Return all products whose quantity is below the given threshold."""
    products = _load_products()
    alerts = []
    for p in products:
        qty = float(p["quantity"])
        if qty < threshold:
            alerts.append(
                {"id": int(p["id"]), "name": p["name"], "quantity": qty, "unit": p["unit"]}
            )
    return alerts


# ---------------------------------------------------------------------------
# Entry point (for direct execution)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.app:APP", host="0.0.0.0", port=8000, reload=True)