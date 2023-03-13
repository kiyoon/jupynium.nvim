; extends

(expression_statement
 ((string) @_var @variable)
 (#match? @_var "^[\"']{3}[%]{2}.*[%]{2}[\"']{3}$")
)

; it can be # %% [markdown] or # %% [md]
((
  (comment) @_mdcomment
  . (expression_statement 
      (string (string_content) @variable)))
  (#lua-match? @_mdcomment "^# %%%% %[markdown%]"))

((
  (comment) @_mdcomment
  . (expression_statement 
      (string (string_content) @variable)))
  (#lua-match? @_mdcomment "^# %%%% %[md%]"))
