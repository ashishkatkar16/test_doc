-- =====================================================
-- Table: public.customers
-- =====================================================
CREATE TABLE IF NOT EXISTS public.customers
(
    id          integer NOT NULL DEFAULT nextval('customers_id_seq'::regclass),
    name        character varying COLLATE pg_catalog."default" NOT NULL,
    email       character varying COLLATE pg_catalog."default",
    phone       character varying COLLATE pg_catalog."default",
    created_at  timestamp without time zone,
    CONSTRAINT customers_pkey PRIMARY KEY (id)
);

-- =====================================================
-- Table: public.document_types
-- =====================================================
CREATE TABLE IF NOT EXISTS public.document_types
(
    id          integer NOT NULL DEFAULT nextval('document_types_id_seq'::regclass),
    name        character varying COLLATE pg_catalog."default" NOT NULL,
    description text COLLATE pg_catalog."default",
    created_at  timestamp without time zone,
    CONSTRAINT document_types_pkey PRIMARY KEY (id)
);

-- =====================================================
-- Table: public.documents
-- =====================================================
CREATE TABLE IF NOT EXISTS public.documents
(
    id            integer NOT NULL DEFAULT nextval('documents_id_seq'::regclass),
    filename      character varying COLLATE pg_catalog."default" NOT NULL,
    file_path     character varying COLLATE pg_catalog."default" NOT NULL,
    status        character varying COLLATE pg_catalog."default",
    created_at    timestamp without time zone,
    processed_at  timestamp without time zone,
    CONSTRAINT documents_pkey PRIMARY KEY (id)
);

-- =====================================================
-- Table: public.policies
-- =====================================================
CREATE TABLE IF NOT EXISTS public.policies
(
    id              integer NOT NULL DEFAULT nextval('policies_id_seq'::regclass),
    policy_number   character varying COLLATE pg_catalog."default" NOT NULL,
    customer_id     integer,
    policy_type     character varying COLLATE pg_catalog."default",
    status          character varying COLLATE pg_catalog."default",
    created_at      timestamp without time zone,
    CONSTRAINT policies_pkey PRIMARY KEY (id),
    CONSTRAINT policies_policy_number_key UNIQUE (policy_number)
);

-- =====================================================
-- Table: public.processing_results
-- =====================================================
CREATE TABLE IF NOT EXISTS public.processing_results
(
    id                          integer   NOT NULL DEFAULT nextval('processing_results_id_seq'::regclass),
    document_id                 integer   NOT NULL,
    extracted_text              text      COLLATE pg_catalog."default",
    customer_match_score        double precision,
    policy_match_score          double precision,
    invoice_reconciliation_score double precision,
    data_quality_score          double precision,
    overall_score               double precision,
    requires_manual_review      boolean,
    created_at                  timestamp without time zone,
    CONSTRAINT processing_results_pkey PRIMARY KEY (id)
);

-- =====================================================
-- Table: public.invoices
-- =====================================================
CREATE TABLE IF NOT EXISTS public.invoices
(
    id              integer NOT NULL DEFAULT nextval('invoices_id_seq'::regclass),
    invoice_number  character varying COLLATE pg_catalog."default" NOT NULL,
    customer_id     integer,
    policy_id       integer,
    amount          numeric(12,2),
    invoice_date    timestamp without time zone,
    due_date        timestamp without time zone,
    status          character varying COLLATE pg_catalog."default",
    description     text COLLATE pg_catalog."default",
    created_at      timestamp without time zone,
    CONSTRAINT invoices_pkey PRIMARY KEY (id),
    CONSTRAINT invoices_invoice_number_key UNIQUE (invoice_number)
);

-- =====================================================
-- Table: public.transactions
-- =====================================================
CREATE TABLE IF NOT EXISTS public.transactions
(
    id                 integer NOT NULL DEFAULT nextval('transactions_id_seq'::regclass),
    transaction_id     character varying COLLATE pg_catalog."default" NOT NULL,
    invoice_id         integer,
    customer_id        integer,
    amount             numeric(12,2),
    transaction_date   timestamp without time zone,
    transaction_type   character varying COLLATE pg_catalog."default",
    payment_method     character varying COLLATE pg_catalog."default",
    status             character varying COLLATE pg_catalog."default",
    reference_number   character varying COLLATE pg_catalog."default",
    created_at         timestamp without time zone,
    CONSTRAINT transactions_pkey PRIMARY KEY (id),
    CONSTRAINT transactions_transaction_id_key UNIQUE (transaction_id)
);