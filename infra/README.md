# Infra

Terraform for the blog API: one Lambda (python3.12, arm64) behind a Lambda
Function URL. No API Gateway, no VPC, no database.

## Cost

- Lambda: always-free tier is 1M requests and 400,000 GB-seconds a month; a
  personal blog stays inside it. Function URLs cost nothing extra.
- CloudWatch Logs: 5 GB a month free; retention is 14 days.
- New AWS accounts (since July 2025) start on a credits-based free plan:
  100 USD on sign-up, up to 200 USD after a few activities, valid six
  months. Enough for this and then some.
- The real bill is DeepSeek tokens. A question costs roughly 6k to 12k input
  tokens and under 1k output on `deepseek-v4-flash`. The account's Lambda
  concurrency quota (10 on a new account) caps how fast that can burn;
  `reserved_concurrency` can tighten it once AWS raises the quota.
- `budget_email` creates an AWS Budget (free) with alerts at 25% and 100%
  of `budget_limit_usd`.

## First deploy (laptop)

```sh
aws configure                          # or aws sso login
make -C ../backend package
cp terraform.tfvars.example terraform.tfvars   # add the DeepSeek key
terraform init
terraform apply
terraform output function_url          # goes into js/config.js
```

State is local until you copy `backend.tf.example` to `backend.tf` and
create the bucket it names.

## Deploy from GitHub Actions

The `deploy` job in `.github/workflows/backend.yml` runs on `main` when two
secrets exist: `DEEPSEEK_API_KEY` and `AWS_ROLE_ARN`. The role must trust
GitHub's OIDC provider (`token.actions.githubusercontent.com`) for
`repo:91Phoenix/built-by-raffa:ref:refs/heads/main` and be allowed to manage
the Lambda, its IAM role, the log group and the state bucket. Optional
repository variables: `AWS_REGION`, `ALLOWED_ORIGIN`.
