-- "Revenue by Country" reports transaction_country, the degenerate dimension on the
-- fact, rather than the customer's country. That choice is only safe while the two
-- agree: if a customer in DE could book a transaction recorded against AT, the card
-- would be answering a different question than a reader assumes.
--
-- In the current source data they never disagree for any row with a resolvable
-- customer. This test turns that observation into an enforced assumption, so the
-- reporting decision documented in data_model.md fails loudly rather than drifting
-- silently if the source data ever changes.
--
-- Rows resolved to the Unknown customer ('-1') are excluded on purpose: that member
-- carries customer_country = 'Unknown' by construction, so it can never match and
-- would make the test permanently fail rather than detect anything.

select
    f.transaction_id,
    f.transaction_country,
    c.customer_country
from "dwh"."mart"."fct_sm_sales" f
join "dwh"."mart"."dim_sm_customer" c
  on c.customer_id = f.customer_id
where f.customer_id <> '-1'
  and f.transaction_country is distinct from c.customer_country