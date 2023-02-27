; extends

; match a string that starts with """%% and ends with %%"""
; or starts with '''%% and ends with %%'''
; and highlight it as markdown
(expression_statement
 ((string) @markdown @markdown_inline)
 (#match? @markdown_inline "^[\"']{3}[%]{2}.*[%]{2}[\"']{3}$")
)
