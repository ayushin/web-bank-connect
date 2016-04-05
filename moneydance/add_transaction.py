#
# An example of adding a downloaded transaction to Moneydance
#
#
#


from com.infinitekind.moneydance.model import OnlineTxn
from com.moneydance.apps.md.view.gui import MDAccountProxy
from datetime import date

account_name = 'Checking'

transactionDateInt = 20160101
transactionName = 'example transaction'
transactionMemo = 'example memo, normally longer than the transaction name'
transactionRefNum = 'UNIQUE0101'
transactionAmountStr = '101,10'
transactionType = 'CREDIT'

newLedgerBalanceAmount = '102,10'
newLedgerBalanceDate = date(2016, 01, 01)

ra = moneydance.getRootAccount()
account = ra.getAccountByName(account_name)

if not account:
    print "no account named %s" % account_name

downloadedTransactions = account.getDownloadedTxns()
newTxn = downloadedTransactions.newTxn()

newTxn.setDatePostedInt(transactionDateInt)
newTxn.setName(transactionName)
newTxn.setMemo(transactionMemo)
newTxn.setRefNum(transactionRefNum)
newTxn.setAmount(account.getCurrencyType().parse(transactionAmountStr, ','))
newTxn.setTxnType(transactionType)

downloadedTransactions.addNewTxn(newTxn)

downloadedTransactions.setOnlineLedgerBalance(account.getCurrencyType().parse(newLedgerBalanceAmount, ','),
                                              newLedgerBalanceDate.toordinal())

# A little MoneyDance magic to get the transactions updated -- thank you Sean!
moneydance.getUI().getOnlineManager().getDefaultUIProxy().receivedStatement(MDAccountProxy(account))


print "Done"