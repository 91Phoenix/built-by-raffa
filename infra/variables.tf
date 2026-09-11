variable "aws_region" {
  description = "Region for the Lambda. eu-west-1 keeps it close to Italy; Function URLs are regional."
  type        = string
  default     = "eu-west-1"
}

variable "name" {
  description = "Base name for every resource."
  type        = string
  default     = "bradicode-blog-api"
}

variable "lambda_zip_path" {
  description = "Path to the zip built by `make -C backend package`."
  type        = string
  default     = "../backend/build/blog_api.zip"
}

variable "deepseek_api_key" {
  description = "DeepSeek API key, passed as a Lambda environment variable (encrypted at rest by AWS)."
  type        = string
  sensitive   = true
}

variable "chat_model" {
  description = "DeepSeek model id used by the chat."
  type        = string
  default     = "deepseek-v4-flash"
}

variable "allowed_origin" {
  description = "Origin allowed by CORS. The blog's public URL in production; '*' while testing."
  type        = string
  default     = "https://bradicode.dev"
}

variable "reserved_concurrency" {
  description = "Hard cap on parallel invocations, or null for none. New accounts start with an account-wide quota of 10 concurrent executions and Lambda refuses a reservation that would leave fewer than 10 unreserved, so this stays null until the account quota is raised. Until then the account quota itself is the burst guard."
  type        = number
  default     = null
}

variable "log_retention_days" {
  type    = number
  default = 14
}

variable "budget_email" {
  description = "Email for cost alerts. Empty string disables the budget."
  type        = string
  default     = ""
}

variable "budget_limit_usd" {
  description = "Monthly cost budget. Alerts at 25% actual, 100% actual and 100% forecasted."
  type        = number
  default     = 20
}
