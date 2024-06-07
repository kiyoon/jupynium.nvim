; extends

; it can be # %% [markdown] or # %% [md]
((
  (comment) @_mdcomment
  . (expression_statement 
      (string (string_content) @markdown @markdown_inline)))
  (#lua-match? @_mdcomment "^# %%%% %[markdown%]"))

((
  (comment) @_mdcomment
  . (expression_statement 
      (string (string_content) @markdown @markdown_inline)))
  (#lua-match? @_mdcomment "^# %%%% %[md%]"))
