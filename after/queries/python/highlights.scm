; extends

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
