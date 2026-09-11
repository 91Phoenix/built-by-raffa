output "function_url" {
  description = "Base URL of the API. Put it in js/config.js as BRADICODE_API_URL."
  value       = aws_lambda_function_url.api.function_url
}

output "function_name" {
  value = aws_lambda_function.api.function_name
}

output "log_group" {
  value = aws_cloudwatch_log_group.lambda.name
}
