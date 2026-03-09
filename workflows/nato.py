"""
Demo 1 : Workflow avec Activities
==================================
Scenario : Pipeline de traitement d'une commande e-commerce

3 activites enchainees :
  1. Valider la commande (stock, client)
  2. Calculer le prix (remises, TVA)
  3. Envoyer la confirmation

Execution 100% locale, pas besoin de Temporal.
Pas besoin d'API Mistral (pas de LLM ici).

Usage :
    uv run python scripts/demo_1_workflow_activities.py
"""

import asyncio
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

import mistralai_workflows as workflows
from loguru import logger
from pydantic import BaseModel


# ──────────────────────────────────────────────
# Modele d'entree du workflow (Pydantic requis)
# ──────────────────────────────────────────────
class OrderItem(BaseModel):
    sku: str
    quantity: int


class OrderWorkflowInput(BaseModel):
    customer_name: str
    customer_email: str
    items: list[OrderItem]


# ──────────────────────────────────────────────
# Activite 1 : Valider la commande
# ──────────────────────────────────────────────
@workflows.activity(
    name="validate_order",
    start_to_close_timeout=timedelta(seconds=5),
    retry_policy_max_attempts=2,
)
async def validate_order(order: dict[str, object]) -> dict[str, object]:
    """Verifie le stock et la validite du client."""
    logger.info(f"Validation de la commande pour {order['customer_name']}...")

    catalog = {
        "LAPTOP-PRO-15": {"name": 'Laptop Pro 15"', "price": 1299.00, "stock": 12},
        "MOUSE-ERGO": {"name": "Souris Ergonomique", "price": 49.99, "stock": 150},
        "SCREEN-4K-27": {"name": "Ecran 4K 27", "price": 599.00, "stock": 0},
    }

    validated_items = []
    for item in order["items"]:  # type: ignore[union-attr]
        product = catalog.get(item["sku"])  # type: ignore[index]
        if not product:
            raise ValueError(f"Produit inconnu : {item['sku']}")  # type: ignore[index]
        if product["stock"] < item["quantity"]:  # type: ignore[index,operator]
            raise ValueError(f"Stock insuffisant pour {product['name']}")

        validated_items.append({
            "sku": item["sku"],  # type: ignore[index]
            "name": product["name"],
            "unit_price": product["price"],
            "quantity": item["quantity"],  # type: ignore[index]
        })

    logger.info(f"  {len(validated_items)} article(s) valide(s)")
    return {
        "customer_name": order["customer_name"],
        "customer_email": order["customer_email"],
        "items": validated_items,
    }


# ──────────────────────────────────────────────
# Activite 2 : Calculer le prix
# ──────────────────────────────────────────────
@workflows.activity(
    name="calculate_pricing",
    start_to_close_timeout=timedelta(seconds=5),
)
async def calculate_pricing(validated_order: dict[str, object]) -> dict[str, object]:
    """Applique les remises et calcule le total TTC."""
    logger.info("Calcul du prix...")

    subtotal = sum(
        item["unit_price"] * item["quantity"]  # type: ignore[index,operator]
        for item in validated_order["items"]  # type: ignore[union-attr]
    )

    # Remise volume : -5% au-dela de 1000 EUR
    discount_rate = 0.05 if subtotal > 1000 else 0.0
    discount_amount = subtotal * discount_rate

    total_ht = subtotal - discount_amount
    tva = total_ht * 0.20
    total_ttc = total_ht + tva

    logger.info(f"  Sous-total : {subtotal:.2f} EUR")
    if discount_amount > 0:
        logger.info(f"  Remise volume (-5%) : -{discount_amount:.2f} EUR")
    logger.info(f"  TVA (20%) : {tva:.2f} EUR")
    logger.info(f"  Total TTC : {total_ttc:.2f} EUR")

    return {
        **validated_order,
        "subtotal": subtotal,
        "discount": discount_amount,
        "tva": tva,
        "total_ttc": round(total_ttc, 2),
    }


# ──────────────────────────────────────────────
# Activite 3 : Envoyer la confirmation
# ──────────────────────────────────────────────
@workflows.activity(
    name="send_confirmation",
    start_to_close_timeout=timedelta(seconds=10),
    retry_policy_max_attempts=3,
)
async def send_confirmation(priced_order: dict[str, object]) -> dict[str, object]:
    """Envoie un email de confirmation (simule)."""
    logger.info(f"Envoi de la confirmation a {priced_order['customer_email']}...")

    await asyncio.sleep(0.5)

    items_summary = "\n".join(
        f"  - {item['name']} x{item['quantity']} : "  # type: ignore[index]
        f"{item['unit_price'] * item['quantity']:.2f} EUR"  # type: ignore[index,operator]
        for item in priced_order["items"]  # type: ignore[union-attr]
    )

    email_body = f"""
    ========================================
    CONFIRMATION DE COMMANDE
    ========================================
    Client : {priced_order['customer_name']}
    Email  : {priced_order['customer_email']}

    Articles :
{items_summary}

    Sous-total : {priced_order['subtotal']:.2f} EUR
    Remise     : -{priced_order['discount']:.2f} EUR
    TVA (20%)  : {priced_order['tva']:.2f} EUR
    ----------------------------------------
    TOTAL TTC  : {priced_order['total_ttc']:.2f} EUR
    ========================================
    """

    logger.info(email_body)
    logger.info("  Email envoye avec succes")

    return {
        "status": "confirmed",
        "order_id": "ORD-2026-00042",
        "total_ttc": priced_order["total_ttc"],
        "customer_email": priced_order["customer_email"],
    }


# ──────────────────────────────────────────────
# Workflow : orchestre les 3 activites
# ──────────────────────────────────────────────
@workflows.workflow.define(name="order_processing_pipeline")
class OrderProcessingWorkflow:
    """Pipeline de traitement de commande en 3 etapes."""

    @workflows.workflow.entrypoint
    async def run(self, input_data: OrderWorkflowInput) -> dict[str, object]:
        order = input_data.model_dump()

        # Etape 1 : Validation
        validated = await validate_order(order)

        # Etape 2 : Calcul du prix
        priced = await calculate_pricing(validated)

        # Etape 3 : Confirmation
        confirmation = await send_confirmation(priced)

        return confirmation


# ──────────────────────────────────────────────
# Point d'entree : execution locale
# ──────────────────────────────────────────────
async def main() -> None:
    logger.info("=== DEMO : Workflow avec Activities (execution locale) ===\n")

    result = await workflows.execute_workflow(
        OrderProcessingWorkflow,
        params=OrderWorkflowInput(
            customer_name="Marie Dupont",
            customer_email="marie.dupont@example.com",
            items=[
                OrderItem(sku="LAPTOP-PRO-15", quantity=1),
                OrderItem(sku="MOUSE-ERGO", quantity=2),
            ],
        ),
    )

    logger.info(f"\nResultat final : {result}")


if __name__ == "__main__":
    asyncio.run(main())