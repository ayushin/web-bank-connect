#
# An example of adding a downloaded transaction to Moneydance
#
#
#


from com.infinitekind.moneydance.model import Account
from com.moneydance.apps.md.view.gui import MDAccountProxy

account_name = 'Credit Card'
account_type = 'CREDIT_CARD'

ra = moneydance.getRootAccount()
ab = moneydance.getCurrentAccountBook()

account = ra.makeAccount(ab, Account.AccountType.valueOf(account_type), ra)
account.setAccountName(account_name)
account.setCreationDate(20120101)

account.syncItem()
