CREATE OR REPLACE FUNCTION public.after_salary_generation_2_trigger()
 RETURNS trigger
 LANGUAGE plpython3u
AS $function$

query_check_depth = "SELECT pg_trigger_depth()"
result = plpy.execute(query_check_depth)
trigger_depth = result[0]["pg_trigger_depth"]

if trigger_depth != 1:
    return 'OK'

query="""select  COALESCE(sum(column70529),0) as sum from table4276 where column70530=%s"""%(TD["new"]["id"])
monthly_gross_deduction=plpy.execute(query)[0]['sum']

query="""select  COALESCE(sum(column70372),0) as sum from table4270 where column70384=%s"""%(TD["new"]["id"])
earned_gross_salary=plpy.execute(query)[0]['sum']

query="""select  COALESCE(sum(column70642),0) as sum from table4280 where column70643=%s"""%(TD["new"]["id"])
monthly_contribution=plpy.execute(query)[0]['sum']


query = """
UPDATE table545 AS a
SET 
    column70359 = b.column69881,
    column70544 = %s,
    column70360 = %s,
    column70579 = %s,
    column70578 = %s,
    column71128 = %s,
    column71129 = %s,
    column8575 =%s-%s
    from (select %s as aid,* from table4107 AS B where b.column67397='%s' and b.column70293<=to_date('%s', 'yyyy-mm-dd') and (b.column70294 is null or b.column70294>=to_date('%s', 'yyyy-mm-dd')) limit 1) as b where a.id=%s and b.aid=%s""" %(monthly_gross_deduction, monthly_gross_deduction, earned_gross_salary, earned_gross_salary, monthly_contribution, monthly_contribution, earned_gross_salary, monthly_gross_deduction, TD["new"]["id"], TD["new"]["column8493"], TD["new"]["column8522"], TD["new"]["column8523"], TD["new"]["id"], TD["new"]["id"])

plpy.execute(query)
plpy.notice(str(TD["new"]))
return 'OK'
$function$