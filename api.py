"""
Alpha Prophet FastAPI Server
Exposes all 12 tools as REST endpoints for the web frontend
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Any
import uvicorn

# Import all tools
from tools import (
    get_distribution,
    analyze_state,
    get_warehouse_info,
    forecast_demand,
    get_backlog_summary,
    compare_routing,
    recommend_east_coast_location,
    search_orders,
    search_freight,
    estimate_shipping_cost,
    compare_routing_cost,
    analyze_cost_savings,
)

app = FastAPI(
    title="Alpha Prophet API",
    description="Warehouse optimization tools for Sediver USA",
    version="1.0.0",
)

# CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request models
class DistributionRequest(BaseModel):
    product_name: str
    quantity: int
    customer_state: Optional[str] = None


class StateRequest(BaseModel):
    state: str


class WarehouseRequest(BaseModel):
    warehouse: str


class ForecastRequest(BaseModel):
    product_name: str
    months: Optional[int] = 3


class BacklogRequest(BaseModel):
    group_by: Optional[str] = "warehouse"


class SearchOrdersRequest(BaseModel):
    customer: Optional[str] = None
    product: Optional[str] = None
    state: Optional[str] = None
    date_range: Optional[str] = None
    limit: Optional[int] = 10


class SearchFreightRequest(BaseModel):
    warehouse: Optional[str] = "all"
    date_range: Optional[str] = None
    destination: Optional[str] = None
    limit: Optional[int] = 10


class EastCoastRequest(BaseModel):
    top_n: Optional[int] = 5


class ShippingCostRequest(BaseModel):
    from_warehouse: str
    to_state: str
    weight_lbs: Optional[float] = None
    pallets: Optional[float] = None
    transport_type: Optional[str] = None


class RoutingCostRequest(BaseModel):
    to_state: str
    weight_lbs: Optional[float] = None
    pallets: Optional[float] = None


class CostSavingsRequest(BaseModel):
    scenario: Optional[str] = "all"


# Helper to wrap responses
def api_response(data: Any):
    if isinstance(data, dict) and "error" in data:
        return {"success": False, "error": data["error"]}
    return {"success": True, "data": data}


# Endpoints
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "Alpha Prophet API"}


@app.post("/api/get-distribution")
async def api_get_distribution(req: DistributionRequest):
    result = get_distribution(req.product_name, req.quantity, req.customer_state)
    return api_response(result)


@app.post("/api/analyze-state")
async def api_analyze_state(req: StateRequest):
    result = analyze_state(req.state)
    return api_response(result)


@app.post("/api/get-warehouse-info")
async def api_get_warehouse_info(req: WarehouseRequest):
    result = get_warehouse_info(req.warehouse)
    return api_response(result)


@app.post("/api/forecast-demand")
async def api_forecast_demand(req: ForecastRequest):
    result = forecast_demand(req.product_name, req.months)
    return api_response(result)


@app.post("/api/get-backlog-summary")
async def api_get_backlog_summary(req: BacklogRequest):
    result = get_backlog_summary(req.group_by)
    return api_response(result)


@app.post("/api/compare-routing")
async def api_compare_routing():
    result = compare_routing()
    return api_response(result)


@app.post("/api/recommend-east-coast-location")
async def api_recommend_east_coast(req: EastCoastRequest):
    result = recommend_east_coast_location(req.top_n)
    return api_response(result)


@app.post("/api/search-orders")
async def api_search_orders(req: SearchOrdersRequest):
    result = search_orders(
        customer=req.customer,
        product=req.product,
        state=req.state,
        date_range=req.date_range,
        limit=req.limit,
    )
    return api_response(result)


@app.post("/api/search-freight")
async def api_search_freight(req: SearchFreightRequest):
    result = search_freight(
        warehouse=req.warehouse,
        date_range=req.date_range,
        destination=req.destination,
        limit=req.limit,
    )
    return api_response(result)


@app.post("/api/estimate-shipping-cost")
async def api_estimate_shipping_cost(req: ShippingCostRequest):
    result = estimate_shipping_cost(
        from_warehouse=req.from_warehouse,
        to_state=req.to_state,
        weight_lbs=req.weight_lbs,
        pallets=req.pallets,
        transport_type=req.transport_type,
    )
    return api_response(result)


@app.post("/api/compare-routing-cost")
async def api_compare_routing_cost(req: RoutingCostRequest):
    result = compare_routing_cost(
        to_state=req.to_state,
        weight_lbs=req.weight_lbs,
        pallets=req.pallets,
    )
    return api_response(result)


@app.post("/api/analyze-cost-savings")
async def api_analyze_cost_savings(req: CostSavingsRequest):
    result = analyze_cost_savings(req.scenario)
    return api_response(result)


if __name__ == "__main__":
    print("\n🔮 Alpha Prophet API Server")
    print("=" * 40)
    print("Starting on http://localhost:8000")
    print("Docs: http://localhost:8000/docs")
    print("=" * 40 + "\n")
    uvicorn.run(app, host="0.0.0.0", port=8000)
