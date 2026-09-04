SELECT название, количество, цена, рейтинг, статус_остатка
from products p 
where статус_остатка = 'Low Stock'
ORDER BY количество