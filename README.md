Terraform plan formatter
========================

Just pipe `terraform plan -no-color` output to this script. This will generate an human readable diff.

```
terraform plan -no-color | terraform-plan-formatter.py
```
