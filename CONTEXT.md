# Restaurant Table Ordering

This context covers dine-in ordering from QR entry through kitchen fulfilment and settlement of the table.

## Language

**Table Session**:
The active dine-in visit opened from a table QR. It contains every order round placed before the table is settled or closed.
_Avoid_: Order session, cart session

**Order Round**:
One submission of selected dishes to the kitchen within a Table Session. A Table Session may contain many Order Rounds.
_Avoid_: Invoice, bill

**Table Invoice**:
The single settlement summary for all Order Rounds in a Table Session. Promotions, loyalty identification, and payment method belong to this invoice.
_Avoid_: Order payment, cart total

**Payment Request**:
The customer's request to settle the Table Invoice using a selected payment method.
_Avoid_: Send order, checkout order
