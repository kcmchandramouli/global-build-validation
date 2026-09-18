terraform {
  required_version = ">= 1.0"
}

resource "local_file" "example" {
  content  = "global-build-validation sample"
  filename = "${path.module}/example.txt"
}
