"""

Money Dance interface.

Author: Alex Yushin <alexis@ww.net>

This module will only work when called from inside of the Moneydance python console

"""

from datetime import date, datetime

from com.moneydance.apps.md.view.gui import MDAccountProxy

import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def download_transactions(connection, ra, moneydance):
    """
    Downloads all the transactions via the specified connection and the configured accounts
    and insert them into Moneydance 'ra' as downloaded transactions.

    Skips the accounts that have 'inactive' attribute set to True.

    :param ra: Moneydance root account to use
    :param connection: Connection to download the transactions from.
    :return:    An array of statements with all the dow
    """

    #
    # 1. Verify the configuration and find out the last_download date and time per account
    #
    for account in connection.accounts:
        # Skip the accounts that are marked as 'inactive'
        if not account.active:
            continue

        # Use the account name as Moneydance name if not specifically configured...
        if not hasattr(account, 'moneydance_name'):
            account.moneydance_name = account.name

        # Make sure we have the account in Moneydance
        # XXX Should be a configuration option to create an account if not existing
        account.md_account = ra.getAccountByName(account.moneydance_name)
        assert account.md_account

        # Set up the last_download date and time unless overriden by configuration...
        # 'None' has no longer a special meaning. If one wants to force the download of all
        # the transactions NEVER should be used to overridde it in CONNECTIONS
        if not account.last_download:
            account.last_download = datetime.utcfromtimestamp(MDAccountProxy(account.md_account).getOFXLastTxnUpdate()/1000)

        logger.info('last download for this account was on %s' % account.last_download)

        # Check if we should download this account again...
        # if timedelta(utcnow - account.last_download) < download_min_period
        #      account account...
        #

    #
    # 2. Download the transactions with the plug-in
    #
    statements = connection.download_statements()

    #
    #
    # 3. Post the transactions to MoneyDance
    #
    #
    for statement in statements:
        account = statement.account

        # Keep track of reserved transactions
        last_download = datetime.utcnow()

        # Get the downloadedTransactions list...
        downloadedTransactions = account.md_account.getDownloadedTxns()

        # Iterate through the transactions we scraped in (2) above
        for transaction in statement.transactions:
            # We do not add reservation, but
            # If we have a reservation --  next time we should start our update from that date...
            if transaction.reservation:
                logger.info('skipping reservation of %s on %s' % (transaction.amount, transaction.date))
                if transaction.date < last_download.date:
                    last_download = datetime.date(transaction.date)
                continue

            # Insert the transaction
            newTxn = downloadedTransactions.newTxn()

            newTxn.setDatePostedInt(int(transaction.date.strftime("%Y%m%d")))
            newTxn.setName(transaction.name)
            newTxn.setMemo(transaction.memo)
            if transaction.refnum:
                newTxn.setRefNum(transaction.refnum)
            newTxn.setFITxnId(transaction.fitid)

            newTxn.setAmount(account.md_account.getCurrencyType().parse(str(transaction.amount), '.'))
            newTxn.setTxnType(transaction.type)

            downloadedTransactions.addNewTxn(newTxn)

        if statement.closing_balance:
            downloadedTransactions.setOnlineLedgerBalance(\
                account.getCurrencyType().parse(str(statement.closing_balance.amount), '.'),
                    long((statement.closing_balance.date - date(1970, 1, 1)).total_seconds()*1000))

        # Update the last download date...
        #
        # One weak spot below can be if some older transactions only appear at some later date, after a
        # weekend for example: sale was done saturday, download was done saturday, transaction was reserved only,
        # sunday we downloaded transactions again, so the download date is sunday, but
        # then monday the saturday transaction was finalised but with the saturday's date
        MDAccountProxy(account.md_account).setOFXLastTxnUpdate(
            long((last_download - datetime(1970, 1, 1)).total_seconds()*1000))

        # A little MoneyDance magic to get the transactions updated -- thank you Sean!
        moneydance.getUI().getOnlineManager().getDefaultUIProxy().receivedStatement(
            MDAccountProxy(account.md_account))


def download_all_transactions(connections, ra, moneydance, config = {}):
    for connection in connections:
        download_transactions(connection = connection, ra = ra, moneydance = moneydance)